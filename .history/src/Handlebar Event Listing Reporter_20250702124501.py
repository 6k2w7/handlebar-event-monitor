import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import logging
import threading
import queue
import time
import urllib3
import ssl
import re
from datetime import datetime, date
import pandas as pd
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def extract_date_from_url(url):
    """Extract date from URL with multiple patterns."""
    decoded_url = unquote(url)
    patterns = [
        r'(\d{2})-(\d{2})-(\d{2})',  # mm-dd-yy
        r'(\d{2})/(\d{2})/(\d{2})',  # mm/dd/yy  
        r'(\d{2})_(\d{2})_(\d{2})',  # mm_dd_yy
    ]
    
    for pattern in patterns:
        match = re.search(pattern, decoded_url)
        if match:
            try:
                month, day, year = match.groups()
                year = f"20{year}"
                return datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d").date()
            except ValueError:
                continue
    return None

def check_single_event(url, event_history, retry_count=0):
    """Check a single event for ticket availability and pricing with retry logic."""
    max_retries = 2
    
    try:
        session = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True},
            ssl_context=ssl._create_unverified_context()
        )
        delay = 0.7 + (retry_count * 0.5)
        time.sleep(delay)
        response = session.get(url, timeout=25, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        page_title = soup.title.string if soup.title else ""
        event_name = "Unknown Event"
        if page_title:
            title_parts = page_title.split(' - ')
            if len(title_parts) > 1:
                for part in title_parts:
                    part = part.strip()
                    if not re.match(r'^\d{2}/\d{2}/\d{2}$', part) and 'Handlebar' not in part:
                        event_name = part
                        break
            else:
                event_name = page_title.split('|')[0].strip()
        ticket_found = False
        price = None
        cart_links = soup.find_all('a', href=re.compile(r'add-to-cart=\d+'))
        if cart_links:
            for cart_link in cart_links:
                parent = cart_link.find_parent('tr')
                if not parent:
                    parent = cart_link.find_parent('div', class_=re.compile(r'ticket|price|cart'))
                if not parent:
                    parent = cart_link.find_parent('td')
                if parent:
                    price_text = parent.get_text()
                    price_match = re.search(r'\$(\d+\.?\d*)', price_text)
                    if price_match:
                        price = price_match.group(0)
                        ticket_found = True
                        break
        if not ticket_found:
            table_rows = soup.find_all('tr')
            for row in table_rows:
                row_text = row.get_text()
                if 'add to cart' in row_text.lower() or 'plus sales taxes' in row_text.lower():
                    price_match = re.search(r'\$(\d+\.?\d*)', row_text)
                    if price_match:
                        price = price_match.group(0)
                        ticket_found = True
                        break
        if not ticket_found:
            page_text = soup.get_text()
            if any(phrase in page_text.lower() for phrase in ['add to cart', 'buy tickets', 'purchase tickets', 'on sale']):
                price_matches = re.findall(r'\$(\d+\.?\d*)', page_text)
                if price_matches:
                    for match in price_matches:
                        price_val = float(match)
                        if 5 <= price_val <= 500:
                            price = f"${match}"
                            ticket_found = True
                            break
        status = "✓ On Sale" if ticket_found else "✗ No Tickets"
        # Update event history
        if url not in event_history:
            event_history[url] = {}
        current_history = event_history[url].get('price_history', []).copy()
        if price:
            current_history.append({
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'price': price
            })
        event_history[url].update({
            'event_name': event_name,
            'last_checked': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price_history': current_history,
            'on_sale': ticket_found
        })
        return {
            'url': url,
            'event_name': event_name,
            'price': price or "--",
            'status': status,
            'on_sale': ticket_found
        }
    except Exception as e:
        # Retry logic for connection errors
        if retry_count < max_retries and ('connection' in str(e).lower() or 'remote' in str(e).lower()):
            return check_single_event(url, event_history, retry_count + 1)
        error_msg = str(e)
        if len(error_msg) > 80:
            error_msg = error_msg[:80] + "..."
        return {
            'url': url,
            'event_name': "Connection Failed",
            'price': "--",
            'status': f"⚠ Error",
            'on_sale': False,
            'error': True
        }

def fetch_links(events_url):
    """Fetch event links from the main events page."""
    session = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True},
        ssl_context=ssl._create_unverified_context()
    )
    response = session.get(events_url, timeout=15, verify=False)
    soup = BeautifulSoup(response.text, 'html.parser')
    event_links = []
    links = soup.find_all('a', href=True)
    found_links = set()
    today = date.today()
    for link in links:
        href = link.get('href')
        text = link.text.strip().lower()
        if href and href not in found_links and 'hb-events' in href:
            # Skip common non-event pages
            skip_patterns = [
                'contact', 'about', 'policy', 'terms', 
                'privacy', 'login', 'register', 'cart',
                'checkout', 'account', 'admin'
            ]
            if any(pattern in href.lower() for pattern in skip_patterns):
                continue
            full_url = urljoin(events_url, href)
            found_links.add(href)
            event_date = extract_date_from_url(full_url)
            if event_date and event_date < today:
                continue  # Skip past events
            # Additional check - skip if URL doesn't look like an event
            if not re.search(r'\d{2}-\d{2}-\d{2}', href):
                continue  # Skip if no date pattern in URL
                
            event_links.append((full_url, event_date.strftime('%m/%d/%y') if event_date else "TBD"))
    return event_links

def generate_pdf_report(filename, all_events, on_sale_events, total_revenue):
    """Generate a professional PDF report."""
    doc = SimpleDocTemplate(filename, pagesize=letter, 
                           rightMargin=50, leftMargin=50, 
                           topMargin=50, bottomMargin=50)
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1d1d1f')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.HexColor('#007aff')
    )
    
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=6,
        textColor=colors.HexColor('#1d1d1f')
    )
    
    # Build story (content)
    story = []
    
    # Header
    story.append(Paragraph("Event Availability Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", summary_style))
    story.append(Spacer(1, 20))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    
    total_events = len(all_events)
    on_sale_count = len(on_sale_events)
    no_tickets = total_events - on_sale_count - sum(1 for e in all_events if 'Error' in e['status'])
    error_count = sum(1 for e in all_events if 'Error' in e['status'])
    
    summary_data = [
        ['Metric', 'Count', 'Percentage'],
        ['Total Events Checked', str(total_events), '100%'],
        ['Events On Sale', str(on_sale_count), f'{(on_sale_count/total_events*100):.1f}%' if total_events > 0 else '0%'],
        ['Events Not Available', str(no_tickets), f'{(no_tickets/total_events*100):.1f}%' if total_events > 0 else '0%'],
        ['Connection Errors', str(error_count), f'{(error_count/total_events*100):.1f}%' if total_events > 0 else '0%'],
    ]
    
    summary_table = Table(summary_data, colWidths=[2.5*inch, 1*inch, 1*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007aff')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d2d2d7')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # Revenue Summary (if applicable)
    if total_revenue > 0:
        story.append(Paragraph("Revenue Summary", heading_style))
        story.append(Paragraph(f"Total Potential Ticket Revenue: <b>${total_revenue:,.2f}</b>", summary_style))
        story.append(Paragraph(f"Average Ticket Price: <b>${total_revenue/on_sale_count:,.2f}</b>", summary_style))
        story.append(Spacer(1, 20))
    
    # Events On Sale Section
    if on_sale_events:
        story.append(Paragraph("Events Currently On Sale", heading_style))
        
        # Create table data for on-sale events
        sale_data = [['Date', 'Event Name', 'Price']]
        for event in sorted(on_sale_events, key=lambda x: x['date']):
            sale_data.append([
                event['date'],
                event['event_name'][:50] + ('...' if len(event['event_name']) > 50 else ''),
                event['price']
            ])
        
        sale_table = Table(sale_data, colWidths=[0.8*inch, 4*inch, 0.8*inch])
        sale_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34c759')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Date column center
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),    # Event name left
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),  # Price column center
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d2d2d7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fff4')])
        ]))
        
        story.append(sale_table)
        story.append(Spacer(1, 30))
    
    # Complete Event List
    story.append(Paragraph("Complete Event Status Report", heading_style))
    
    # Create table data for all events
    table_data = [['Date', 'Event Name', 'Price', 'Status']]
    for event in sorted(all_events, key=lambda x: x['date']):
        # Truncate long event names
        event_name = event['event_name'][:45] + ('...' if len(event['event_name']) > 45 else '')
        
        # Clean up status for display
        status = event['status'].replace('✓ ', '').replace('✗ ', '').replace('⚠ ', '')
        
        table_data.append([
            event['date'],
            event_name,
            event['price'],
            status
        ])
    
    # Create table
    table = Table(table_data, colWidths=[0.8*inch, 3.5*inch, 0.8*inch, 1*inch])
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1d1d1f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # Event names left-aligned
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d2d2d7')),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    
    # Color-code status cells
    for i, event in enumerate(all_events, 1):
        if 'On Sale' in event['status']:
            table.setStyle(TableStyle([
                ('BACKGROUND', (3, i), (3, i), colors.HexColor('#f0fff4')),
                ('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#34c759'))
            ]))
        elif 'Error' in event['status']:
            table.setStyle(TableStyle([
                ('BACKGROUND', (3, i), (3, i), colors.HexColor('#fffaf0')),
                ('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#ff9500'))
            ]))
        else:  # No tickets
            table.setStyle(TableStyle([
                ('BACKGROUND', (3, i), (3, i), colors.HexColor('#fff5f5')),
                ('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#ff3b30'))
            ]))
    
    story.append(table)
    story.append(Spacer(1, 30))
    
    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#d2d2d7')))
    story.append(Spacer(1, 10))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#86868b')
    )
    
    story.append(Paragraph(f"Report generated by Event Monitor • {datetime.now().strftime('%B %d, %Y')}", footer_style))
    story.append(Paragraph("This report shows current ticket availability and pricing for all checked events.", footer_style))
    
    # Build PDF
    doc.build(story)
    
    return filename

def main():
    st.set_page_config(page_title="Event Ticket Monitor", layout="wide")
    st.title("Event Ticket Monitor")
    st.caption("Track ticket availability and pricing for your events")
    
    # Session state for persistent data
    if 'event_links' not in st.session_state:
        st.session_state.event_links = []
    if 'event_results' not in st.session_state:
        st.session_state.event_results = []
    if 'event_history' not in st.session_state:
        if os.path.exists('event_history.json'):
            with open('event_history.json', 'r') as f:
                st.session_state.event_history = json.load(f)
        else:
            st.session_state.event_history = {}
    
    # URL input
    events_url = st.text_input("Events Page URL", value="https://thehandlebar850.com/events")
    col1, col2, col3 = st.columns(3)
    
    if col1.button("Fetch Events"):
        with st.spinner("Fetching event links..."):
            try:
                st.session_state.event_links = fetch_links(events_url)
                st.success(f"Found {len(st.session_state.event_links)} upcoming events.")
            except Exception as e:
                st.error(f"Error fetching events: {e}")
    
    # Show event links
    if st.session_state.event_links:
        st.subheader("Upcoming Events")
        df = pd.DataFrame(st.session_state.event_links, columns=["URL", "Date"])
        df['Select'] = True
        selected = st.data_editor(df, use_container_width=True, num_rows="dynamic", disabled=["URL", "Date"])
        
        # Check selected events
        if col2.button("Check Selected"):
            selected_urls = [row["URL"] for idx, row in selected.iterrows() if row["Select"]]
            if not selected_urls:
                st.warning("Please select at least one event.")
            else:
                results = []
                progress = st.progress(0)
                for i, url in enumerate(selected_urls):
                    result = check_single_event(url, st.session_state.event_history)
                    # Save event history after each check
                    with open('event_history.json', 'w') as f:
                        json.dump(st.session_state.event_history, f, indent=4)
                    results.append({
                        "Date": next((d for u, d in st.session_state.event_links if u == url), "TBD"),
                        "Event Name": result['event_name'],
                        "Price": result['price'],
                        "Status": result['status'],
                        "URL": url
                    })
                    progress.progress((i+1)/len(selected_urls))
                st.session_state.event_results = results
                st.success("Event scan completed.")
        
        # Show results table
        if st.session_state.event_results:
            st.subheader("Event Results")
            st.dataframe(pd.DataFrame(st.session_state.event_results), use_container_width=True)
            
            # Status counters
            total = len(st.session_state.event_results)
            on_sale = sum(1 for r in st.session_state.event_results if "On Sale" in r["Status"])
            no_tickets = sum(1 for r in st.session_state.event_results if "No Tickets" in r["Status"])
            errors = sum(1 for r in st.session_state.event_results if "Error" in r["Status"])
            st.info(f"Total: {total} | On Sale: {on_sale} | No Tickets: {no_tickets} | Errors: {errors}")
            
            # Export PDF
            if col3.button("Export PDF Report"):
                all_events = st.session_state.event_results
                on_sale_events = [e for e in all_events if "On Sale" in e["Status"] and e["Price"] != "--"]
                total_revenue = 0
                for e in on_sale_events:
                    try:
                        price = float(str(e["Price"]).replace("$", "").replace(",", ""))
                        total_revenue += price
                    except:
                        pass
                # Generate PDF to a temp file
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    filename = tmp.name
                generate_pdf_report(filename, all_events, on_sale_events, total_revenue)
                with open(filename, "rb") as f:
                    st.download_button("Download PDF Report", f, file_name="Event_Report.pdf", mime="application/pdf")
    
    # Show event history (optional)
    with st.expander("Show Event History (JSON)", expanded=False):
        st.json(st.session_state.event_history)

if __name__ == "__main__":
    main()