import cloudscraper
from bs4 import BeautifulSoup
import streamlit as st
import threading
import queue
import logging
from urllib.parse import urljoin, unquote
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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Streamlit App ---

st.set_page_config(page_title="Event Ticket Monitor", layout="wide")

# --- Session State Initialization ---
if 'event_links' not in st.session_state:
    st.session_state.event_links = []
if 'event_history' not in st.session_state:
    st.session_state.event_history = {}
if 'results' not in st.session_state:
    st.session_state.results = []
if 'status_counters' not in st.session_state:
    st.session_state.status_counters = {'total': 0, 'on_sale': 0, 'no_tickets': 0, 'errors': 0}
if 'selected_events' not in st.session_state:
    st.session_state.selected_events = set()
if 'progress' not in st.session_state:
    st.session_state.progress = 0.0
if 'log_messages' not in st.session_state:
    st.session_state.log_messages = []

# --- Helper Functions ---

def log_message(message, level="INFO"):
    st.session_state.log_messages.append((datetime.now().strftime("%H:%M:%S"), message, level))

def save_event_history():
    try:
        with open('event_history.json', 'w') as f:
            json.dump(st.session_state.event_history, f, indent=4)
    except Exception:
        pass

def load_event_history():
    try:
        if os.path.exists('event_history.json'):
            with open('event_history.json', 'r') as f:
                st.session_state.event_history = json.load(f)
    except Exception as e:
        log_message(f"Error loading event history: {str(e)}", "ERROR")

def update_event_history(url, event_name, price=None, on_sale=None):
    try:
        if url not in st.session_state.event_history:
            st.session_state.event_history[url] = {}
        current_history = st.session_state.event_history[url].get('price_history', []).copy()
        if price:
            current_history.append({
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'price': price
            })
        st.session_state.event_history[url].update({
            'event_name': event_name,
            'last_checked': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price_history': current_history,
            'on_sale': on_sale
        })
        save_event_history()
    except Exception as e:
        log_message(f"Error updating event history: {str(e)}", "ERROR")

def extract_date_from_url(url):
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

def fetch_links(events_url):
    log_message("Scanning for events...", "INFO")
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
        if href and href not in found_links and 'hb-events' in href:
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
                continue
            if not re.search(r'\d{2}-\d{2}-\d{2}', href):
                continue
            event_links.append((full_url, event_date.strftime('%m/%d/%y') if event_date else "TBD
        
        # URL input card
        self.setup_url_card(main_frame)
        
        # Main content area
        self.setup_main_content(main_frame)

    def setup_apple_theme(self):
        """Configure Apple-style ttk theme"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure styles with Apple aesthetics
        style.configure('Apple.TFrame', background=self.colors['bg'])
        style.configure('Card.TFrame', background=self.colors['card_bg'], relief='flat')
        
        style.configure('Apple.TLabel', 
                       background=self.colors['bg'], 
                       foreground=self.colors['text_primary'],
                       font=('SF Pro Display', 11))
        
        style.configure('Title.TLabel', 
                       background=self.colors['bg'], 
                       foreground=self.colors['text_primary'],
                       font=('SF Pro Display', 28, 'bold'))
        
        style.configure('Subtitle.TLabel', 
                       background=self.colors['bg'], 
                       foreground=self.colors['text_secondary'],
                       font=('SF Pro Display', 14))
        
        style.configure('Card.TLabel', 
                       background=self.colors['card_bg'], 
                       foreground=self.colors['text_primary'],
                       font=('SF Pro Text', 10))
        
        style.configure('Apple.TButton',
                       background=self.colors['accent'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       font=('SF Pro Text', 11, 'bold'))
        
        style.map('Apple.TButton',
                 background=[('active', '#0051d5'),  # Darker blue on hover
                           ('pressed', '#004bb5')])
        
        style.configure('Apple.TEntry',
                       fieldbackground=self.colors['card_bg'],
                       borderwidth=1,
                       relief='solid',
                       font=('SF Pro Text', 11))

    def setup_header(self, parent):
        """Create Apple-style header"""
        header_frame = tk.Frame(parent, bg=self.colors['bg'])
        header_frame.pack(fill='x', pady=(0, 40))
        
        # Title and subtitle
        title_label = ttk.Label(header_frame, text="Event Monitor", style='Title.TLabel')
        title_label.pack(anchor='w')
        
        subtitle_label = ttk.Label(header_frame, text="Track ticket availability and pricing for your events", style='Subtitle.TLabel')
        subtitle_label.pack(anchor='w', pady=(5, 0))

    def setup_status_cards(self, parent):
        """Create Apple-style status cards"""
        cards_frame = tk.Frame(parent, bg=self.colors['bg'])
        cards_frame.pack(fill='x', pady=(0, 30))
        
        self.status_vars = {
            'total': tk.StringVar(value="0"),
            'on_sale': tk.StringVar(value="0"),
            'no_tickets': tk.StringVar(value="0"),
            'errors': tk.StringVar(value="0")
        }
        
        card_configs = [
            ('Total Events', 'total', self.colors['text_secondary']),
            ('On Sale', 'on_sale', self.colors['success']),
            ('No Tickets', 'no_tickets', self.colors['error']),
            ('Errors', 'errors', self.colors['warning'])
        ]
        
        for i, (title, key, color) in enumerate(card_configs):
            card = tk.Frame(cards_frame, bg=self.colors['card_bg'], relief='flat', bd=1)
            card.pack(side='left', fill='x', expand=True, padx=(0, 15 if i < 3 else 0))
            
            # Add subtle shadow effect
            shadow = tk.Frame(card, bg='#e5e5ea', height=1)
            shadow.pack(side='bottom', fill='x')
            
            # Card content
            content_frame = tk.Frame(card, bg=self.colors['card_bg'])
            content_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            title_label = tk.Label(content_frame, text=title, 
                                 bg=self.colors['card_bg'], 
                                 fg=self.colors['text_secondary'],
                                 font=('SF Pro Text', 11))
            title_label.pack(anchor='w')
            
            value_label = tk.Label(content_frame, textvariable=self.status_vars[key],
                                 bg=self.colors['card_bg'], 
                                 fg=color,
                                 font=('SF Pro Display', 24, 'bold'))
            value_label.pack(anchor='w', pady=(5, 0))

    def setup_url_card(self, parent):
        """Create Apple-style URL input card"""
        url_card = tk.Frame(parent, bg=self.colors['card_bg'], relief='flat', bd=1)
        url_card.pack(fill='x', pady=(0, 30))
        
        # Card shadow
        shadow = tk.Frame(url_card, bg='#e5e5ea', height=1)
        shadow.pack(side='bottom', fill='x')
        
        # Card content
        content_frame = tk.Frame(url_card, bg=self.colors['card_bg'])
        content_frame.pack(fill='both', expand=True, padx=25, pady=25)
        
        # URL input section
        url_label = tk.Label(content_frame, text="Events Page URL", 
                           bg=self.colors['card_bg'], 
                           fg=self.colors['text_primary'],
                           font=('SF Pro Text', 12, 'bold'))
        url_label.pack(anchor='w')
        
        self.url_var = tk.StringVar(value="https://thehandlebar850.com/events")
        url_entry = tk.Entry(content_frame, textvariable=self.url_var, 
                           bg=self.colors['card_bg'],
                           fg=self.colors['text_primary'],
                           relief='solid',
                           bd=1,
                           highlightthickness=1,
                           highlightcolor=self.colors['accent'],
                           font=('SF Pro Text', 11))
        url_entry.pack(fill='x', pady=(8, 15))
        
        # Buttons frame
        buttons_frame = tk.Frame(content_frame, bg=self.colors['card_bg'])
        buttons_frame.pack(fill='x')
        
        # Apple-style buttons
        self.fetch_button = self.create_apple_button(buttons_frame, "Fetch Events", self.fetch_links, primary=False)
        self.fetch_button.pack(side='left', padx=(0, 12))
        
        self.check_button = self.create_apple_button(buttons_frame, "Check Selected", self.start_threaded_check, primary=True)
        self.check_button.pack(side='left', padx=(0, 12))
        self.check_button.config(state='disabled')
        
        self.stop_button = self.create_apple_button(buttons_frame, "Stop", self.stop_check, primary=False)
        self.stop_button.pack(side='left', padx=(0, 12))
        self.stop_button.config(state='disabled')
        
        self.export_button = self.create_apple_button(buttons_frame, "Export PDF Report", self.export_results, primary=False)
        self.export_button.pack(side='left')

    def create_apple_button(self, parent, text, command, primary=True):
        """Create an Apple-style button"""
        if primary:
            bg_color = self.colors['accent']
            fg_color = 'white'
            hover_color = '#0051d5'
        else:
            bg_color = '#f2f2f7'
            fg_color = self.colors['text_primary']
            hover_color = '#e5e5ea'
        
        button = tk.Button(parent, text=text, command=command,
                          bg=bg_color, fg=fg_color,
                          font=('SF Pro Text', 11, 'bold'),
                          relief='flat', bd=0,
                          padx=20, pady=8,
                          cursor='hand2')
        
        # Hover effects
        def on_enter(e):
            button.config(bg=hover_color)
        
        def on_leave(e):
            button.config(bg=bg_color)
        
        button.bind('<Enter>', on_enter)
        button.bind('<Leave>', on_leave)
        
        return button

    def setup_main_content(self, parent):
        """Setup main content area with Apple styling"""
        content_card = tk.Frame(parent, bg=self.colors['card_bg'], relief='flat', bd=1)
        content_card.pack(fill='both', expand=True)
        
        # Card shadow
        shadow = tk.Frame(content_card, bg='#e5e5ea', height=1)
        shadow.pack(side='bottom', fill='x')
        
        # Progress section
        progress_frame = tk.Frame(content_card, bg=self.colors['card_bg'])
        progress_frame.pack(fill='x', padx=25, pady=(25, 15))
        
        self.progress_var = tk.StringVar(value="Ready to scan events")
        progress_label = tk.Label(progress_frame, textvariable=self.progress_var,
                                bg=self.colors['card_bg'], 
                                fg=self.colors['text_secondary'],
                                font=('SF Pro Text', 11))
        progress_label.pack(anchor='w')
        
        # Custom progress bar
        progress_container = tk.Frame(progress_frame, bg='#f2f2f7', height=4)
        progress_container.pack(fill='x', pady=(8, 0))
        progress_container.pack_propagate(False)
        
        self.progress_fill = tk.Frame(progress_container, bg=self.colors['accent'], height=4)
        self.progress_fill.pack(side='left', fill='y')
        
        # Notebook with Apple styling
        self.notebook = ttk.Notebook(content_card)
        self.notebook.pack(fill='both', expand=True, padx=25, pady=(0, 25))

        # Events tab
        self.events_tab = tk.Frame(self.notebook, bg=self.colors['card_bg'])
        self.notebook.add(self.events_tab, text="Events")
        self.setup_events_tab()

        # Activity tab
        self.logs_tab = tk.Frame(self.notebook, bg=self.colors['card_bg'])
        self.notebook.add(self.logs_tab, text="Activity")
        self.setup_logs_tab()

    def setup_events_tab(self):
        """Setup events tab with Apple styling"""
        # Controls
        controls_frame = tk.Frame(self.events_tab, bg=self.colors['card_bg'])
        controls_frame.pack(fill='x', pady=(15, 20))
        
        # Filter dropdown
        filter_label = tk.Label(controls_frame, text="Filter:", 
                              bg=self.colors['card_bg'], 
                              fg=self.colors['text_primary'],
                              font=('SF Pro Text', 11))
        filter_label.pack(side='left', padx=(0, 8))
        
        self.filter_var = tk.StringVar(value="All Events")
        filter_combo = ttk.Combobox(controls_frame, textvariable=self.filter_var, 
                                   values=["All Events", "On Sale Only", "No Tickets Only", "Errors Only"],
                                   state='readonly', width=15, font=('SF Pro Text', 10))
        filter_combo.pack(side='left', padx=(0, 20))
        filter_combo.bind('<<ComboboxSelected>>', self.apply_filter)
        
        # Select all
        self.select_all_var = tk.BooleanVar(value=True)
        select_all_cb = tk.Checkbutton(controls_frame, text="Select All", 
                                     variable=self.select_all_var, 
                                     command=self.toggle_select_all,
                                     bg=self.colors['card_bg'],
                                     fg=self.colors['text_primary'],
                                     font=('SF Pro Text', 11),
                                     relief='flat')
        select_all_cb.pack(side='left')

        # Treeview with Apple styling
        tree_frame = tk.Frame(self.events_tab, bg=self.colors['card_bg'])
        tree_frame.pack(fill='both', expand=True)
        
        columns = ('Select', 'Date', 'Event Name', 'Price', 'Status')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=25)
        
        # Configure columns with Apple fonts
        self.tree.heading('Select', text='✓', anchor='center')
        self.tree.heading('Date', text='Date', anchor='center')
        self.tree.heading('Event Name', text='Event', anchor='w')
        self.tree.heading('Price', text='Price', anchor='center')
        self.tree.heading('Status', text='Status', anchor='center')
        
        self.tree.column('Select', width=60, anchor='center')
        self.tree.column('Date', width=100, anchor='center')
        self.tree.column('Event Name', width=700, anchor='w')
        self.tree.column('Price', width=120, anchor='center')
        self.tree.column('Status', width=150, anchor='center')
        
        # Configure tree styling
        self.tree.tag_configure('on_sale', background='#f0fff4', foreground=self.colors['success'])
        self.tree.tag_configure('no_tickets', background='#fff5f5', foreground=self.colors['error'])
        self.tree.tag_configure('error', background='#fffaf0', foreground=self.colors['warning'])
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        v_scrollbar.pack(side='right', fill='y')
        
        # Bind events
        self.tree.bind('<Double-1>', self.toggle_item_selection)

    def setup_logs_tab(self):
        """Setup logs tab with Apple styling"""
        logs_frame = tk.Frame(self.logs_tab, bg=self.colors['card_bg'])
        logs_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        self.log_text = scrolledtext.ScrolledText(logs_frame, 
                                                 height=30, 
                                                 bg=self.colors['card_bg'],
                                                 fg=self.colors['text_primary'],
                                                 font=('SF Mono', 10),
                                                 relief='flat',
                                                 wrap=tk.WORD)
        self.log_text.pack(fill='both', expand=True)
        
        # Configure log tags with Apple colors
        self.log_text.tag_configure("ERROR", foreground=self.colors['error'])
        self.log_text.tag_configure("SUCCESS", foreground=self.colors['success'])
        self.log_text.tag_configure("WARNING", foreground=self.colors['warning'])
        self.log_text.tag_configure("INFO", foreground=self.colors['text_secondary'])

    def log_message(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, formatted_message, level)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
        # Also log to file
        self.logger.info(f"{level}: {message}")

    def update_progress(self, current, total):
        """Update Apple-style progress bar"""
        if total > 0:
            progress_percent = current / total
            # Update progress bar width
            self.progress_fill.config(width=int(progress_percent * 300))  # Assuming max width of 300px

    def extract_date_from_url(self, url):
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

    def fetch_links(self):
        """Fetch event links from the main events page."""
        try:
            self.log_message("Scanning for events...", "INFO")
            events_url = self.url_var.get().strip()
            
            response = self.session.get(events_url, timeout=15, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Clear previous data
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            self.event_links = []
            links = soup.find_all('a', href=True)
            found_links = set()
            today = date.today()
            
            for link in links:
                href = link.get('href')
                text = link.text.strip().lower()
                
                # More specific filtering to avoid unwanted pages
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
                    
                    event_date = self.extract_date_from_url(full_url)
                    if event_date and event_date < today:
                        continue  # Skip past events
                    
                    # Additional check - skip if URL doesn't look like an event
                    if not re.search(r'\d{2}-\d{2}-\d{2}', href):
                        continue  # Skip if no date pattern in URL
                        
                    self.event_links.append(full_url)
                    
                    # Add to tree with Apple styling
                    item_id = self.tree.insert('', 'end', values=(
                        '☑',  # Selected by default
                        event_date.strftime('%m/%d/%y') if event_date else "TBD",
                        "Loading event details...",
                        "--",
                        "Ready",
                        full_url  # Hidden column for URL
                    ))
            
            self.update_status_counters()
            self.log_message(f"Found {len(self.event_links)} upcoming events", "SUCCESS")
            self.check_button.config(state='normal')
            
        except Exception as e:
            self.log_message(f"Error scanning events: {str(e)}", "ERROR")

    def check_single_event(self, url, retry_count=0):
        """Check a single event for ticket availability and pricing with retry logic."""
        max_retries = 2
        
        try:
            # Create a fresh session for each request
            session = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True},
                ssl_context=ssl._create_unverified_context()
            )
            
            # Progressive delay - longer for retries
            delay = 0.7 + (retry_count * 0.5)
            time.sleep(delay)
            
            response = session.get(url, timeout=25, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract event name from title - improved parsing
            page_title = soup.title.string if soup.title else ""
            event_name = "Unknown Event"
            
            if page_title:
                # Split by common separators and take the first meaningful part
                title_parts = page_title.split(' - ')
                if len(title_parts) > 1:
                    # Take the part that looks like an event name (not just a date)
                    for part in title_parts:
                        part = part.strip()
                        # Skip if it's just a date or venue name
                        if not re.match(r'^\d{2}/\d{2}/\d{2}$', part) and 'Handlebar' not in part:
                            event_name = part
                            break
                else:
                    # No separator, use the whole title but clean it up
                    event_name = page_title.split('|')[0].strip()
            
            # Look for ticket table or pricing info
            ticket_found = False
            price = None
            
            # Method 1: Look for "Add to cart" buttons with pricing
            cart_links = soup.find_all('a', href=re.compile(r'add-to-cart=\d+'))
            if cart_links:
                # Look for price near the cart button or in the same row
                for cart_link in cart_links:
                    # Check parent elements for price information
                    parent = cart_link.find_parent('tr')
                    if not parent:
                        parent = cart_link.find_parent('div', class_=re.compile(r'ticket|price|cart'))
                    if not parent:
                        parent = cart_link.find_parent('td')
                    
                    if parent:
                        price_text = parent.get_text()
                        # Look for price patterns
                        price_match = re.search(r'\$(\d+\.?\d*)', price_text)
                        if price_match:
                            price = price_match.group(0)
                            ticket_found = True
                            break
            
            # Method 2: Look for structured ticket table
            if not ticket_found:
                # Look for table rows with ticket information
                table_rows = soup.find_all('tr')
                for row in table_rows:
                    row_text = row.get_text()
                    if 'add to cart' in row_text.lower() or 'plus sales taxes' in row_text.lower():
                        price_match = re.search(r'\$(\d+\.?\d*)', row_text)
                        if price_match:
                            price = price_match.group(0)
                            ticket_found = True
                            break
            
            # Method 3: Look for price in page content
            if not ticket_found:
                page_text = soup.get_text()
                # Look for common ticket sale indicators
                if any(phrase in page_text.lower() for phrase in ['add to cart', 'buy tickets', 'purchase tickets', 'on sale']):
                    price_matches = re.findall(r'\$(\d+\.?\d*)', page_text)
                    if price_matches:
                        # Take the first reasonable price (between $5 and $500)
                        for match in price_matches:
                            price_val = float(match)
                            if 5 <= price_val <= 500:
                                price = f"${match}"
                                ticket_found = True
                                break
            
            status = "✓ On Sale" if ticket_found else "✗ No Tickets"
            self.update_event_history(url, event_name, price, ticket_found)
            
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
                self.log_message(f"Connection issue with {event_name if 'event_name' in locals() else 'event'}, retrying... ({retry_count + 1}/{max_retries + 1})", "WARNING")
                return self.check_single_event(url, retry_count + 1)
            
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

    def start_threaded_check(self):
        """Start checking events using threading."""
        if self.is_checking:
            return
            
        # Get selected events
        selected_urls = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if values[0] == '☑':  # If selected
                selected_urls.append(values[5])  # URL is in last column
        
        if not selected_urls:
            messagebox.showwarning("No Selection", "Please select at least one event to check.")
            return
        
        self.is_checking = True
        self.check_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.fetch_button.config(state='disabled')
        
        # Start checking in a separate thread
        self.check_thread = threading.Thread(target=self.threaded_check_worker, args=(selected_urls,))
        self.check_thread.daemon = True
        self.check_thread.start()
        
        # Start result processor
        self.root.after(100, self.process_results)

    def threaded_check_worker(self, urls):
        """Worker method that runs the threaded checking."""        
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all tasks
            future_to_url = {executor.submit(self.check_single_event, url): url for url in urls}
            
            completed = 0
            total = len(urls)
            for future in as_completed(future_to_url):
                if not self.is_checking:
                    break
                    
                result = future.result()
                self.result_queue.put(result)
                
                completed += 1
                self.update_progress(completed, total)
                self.progress_var.set(f"Checking events... {completed}/{total}")
        
        # Signal completion
        self.result_queue.put({'completed': True})

    def process_results(self):
        """Process results from the queue and update UI."""
        try:
            while True:
                result = self.result_queue.get_nowait()
                
                if 'completed' in result:
                    # Checking completed
                    self.is_checking = False
                    self.check_button.config(state='normal')
                    self.stop_button.config(state='disabled')
                    self.fetch_button.config(state='normal')
                    self.progress_var.set("Scan complete")
                    self.log_message("Event scan completed", "SUCCESS")
                    self.update_status_counters()
                    return
                
                # Update tree with result
                self.update_tree_item(result)
                
                # Log result
                if result.get('error'):
                    self.log_message(f"Error: {result['event_name']}", "ERROR")
                elif result['on_sale']:
                    self.log_message(f"✓ {result['event_name']} - {result['price']}", "SUCCESS")
                else:
                    self.log_message(f"✗ {result['event_name']} - No tickets available", "WARNING")
                    
        except queue.Empty:
            pass
        
        if self.is_checking:
            self.root.after(100, self.process_results)

    def update_tree_item(self, result):
        """Update a tree item with check results."""
        url = result['url']
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if len(values) > 5 and values[5] == url:
                # Determine row styling based on result
                if result['on_sale']:
                    tag = 'on_sale'
                elif result.get('error'):
                    tag = 'error'
                else:
                    tag = 'no_tickets'
                
                # Update the item
                self.tree.item(item, values=(
                    values[0],  # Keep selection status
                    values[1],  # Keep date
                    result['event_name'],
                    result['price'],
                    result['status'],
                    url
                ), tags=(tag,))
                break

    def update_status_counters(self):
        """Update the status counter display."""
        total = len(self.tree.get_children())
        on_sale = 0
        no_tickets = 0
        errors = 0
        
        for item in self.tree.get_children():
            status = self.tree.item(item)['values'][4]
            if 'On Sale' in str(status):
                on_sale += 1
            elif 'Error' in str(status):
                errors += 1
            elif 'No Tickets' in str(status):
                no_tickets += 1
        
        self.status_vars['total'].set(str(total))
        self.status_vars['on_sale'].set(str(on_sale))
        self.status_vars['no_tickets'].set(str(no_tickets))
        self.status_vars['errors'].set(str(errors))

    def toggle_item_selection(self, event):
        """Toggle selection of an item when double-clicked."""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            values = list(self.tree.item(item)['values'])
            values[0] = '☐' if values[0] == '☑' else '☑'
            self.tree.item(item, values=values)

    def toggle_select_all(self):
        """Toggle selection of all items."""
        select_symbol = '☑' if self.select_all_var.get() else '☐'
        for item in self.tree.get_children():
            values = list(self.tree.item(item)['values'])
            values[0] = select_symbol
            self.tree.item(item, values=values)

    def apply_filter(self, event=None):
        """Apply filter to the tree view."""
        filter_value = self.filter_var.get()
        
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            status = str(values[4])
            
            show_item = True
            if filter_value == "On Sale Only" and "On Sale" not in status:
                show_item = False
            elif filter_value == "No Tickets Only" and "No Tickets" not in status:
                show_item = False
            elif filter_value == "Errors Only" and "Error" not in status:
                show_item = False
            
            # Hide/show item
            if show_item:
                self.tree.reattach(item, '', 'end')
            else:
                self.tree.detach(item)

    def stop_check(self):
        """Stop the checking process."""
        self.is_checking = False
        self.log_message("Stopping scan...", "WARNING")

    def export_results(self):
        """Export results to professional PDF report."""
        try:
            print("Starting export...")
            self.log_message("Starting export process", "INFO")
            
            # Get data from tree
            data = []
            on_sale_events = []
            total_revenue = 0
            
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                event_data = {
                    'date': values[1],
                    'event_name': values[2],
                    'price': values[3],
                    'status': values[4],
                    'url': values[5] if len(values) > 5 else ''
                }
                data.append(event_data)
                
                # Track on-sale events for summary
                if 'On Sale' in str(values[4]) and values[3] != '--':
                    on_sale_events.append(event_data)
                    # Extract price for revenue calculation
                    price_str = str(values[3]).replace(',', '').replace(',', '')
                    try:
                        price = float(price_str)
                        total_revenue += price
                    except:
                        pass
            
            print(f"Found {len(data)} events")
            self.log_message(f"Found {len(data)} events to export", "INFO")
            
            if not data:
                self.log_message("No data to export", "WARNING")
                return
            
            # Test if filedialog is available
            print("About to show file dialog...")
            self.log_message("About to show file dialog", "INFO")
            
            from tkinter import filedialog
            
            # Generate default filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_filename = f'Event_Report_{timestamp}.pdf'
            
            print(f"Default filename: {default_filename}")
            
            # Show save dialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialfile=default_filename,
                title="Save Event Report As"
            )
            
            print(f"Selected filename: {filename}")
            self.log_message(f"User selected filename: {filename}", "INFO")
            
            # If user cancelled the dialog, filename will be empty
            if not filename:
                self.log_message("Export cancelled by user", "INFO")
                return
            
            # Generate PDF report
            self.generate_pdf_report(filename, data, on_sale_events, total_revenue)
            self.log_message(f"Professional report exported: {filename}", "SUCCESS")
                
        except Exception as e:
            print(f"Error in export: {str(e)}")
            self.log_message(f"Export error: {str(e)}", "ERROR")

    def generate_pdf_report(self, filename, all_events, on_sale_events, total_revenue):
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

    def run(self):
        """Run the application."""
        # Center window on screen
        self.root.update_idletasks()
        width = 1500
        height = 1000
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Set minimum window size
        self.root.minsize(1200, 800)
        
        self.root.mainloop()

if __name__ == "__main__":
    app = AppleStyleEventChecker()
    app.run()