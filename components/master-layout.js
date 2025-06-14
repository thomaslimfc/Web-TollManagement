class MasterLayout extends HTMLElement {
  constructor() {
    super();
    const shadowRoot = this.attachShadow({ mode: 'open' });
    
    // CSS with consistent styling
    const style = document.createElement('style');
    style.textContent = `
      :host {
        display: block;
        --header-height: 70px;
        --sidebar-width: 280px;
        --primary-color: #003ead;
        --text-light: #ffffff;
        --font-main: 'Segoe UI', Arial, sans-serif;
        --transition-speed: 0.2s;
      }
      
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
        font-family: var(--font-main);
      }
      
      /* Top Navigation */
      #navTop {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: var(--header-height);
        background: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0 25px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        z-index: 1000;
      }
      
      #navTop img {
        height: 50px;
        transition: transform var(--transition-speed);
      }
      
      #navTop img:hover {
        transform: scale(1.05);
      }
      
      /* Sidebar */
      #sidebar {
        position: fixed;
        top: var(--header-height);
        left: 0;
        bottom: 0;
        width: var(--sidebar-width);
        background: var(--primary-color);
        color: var(--text-light);
        transition: transform var(--transition-speed) ease;
        z-index: 999;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: rgba(255,255,255,0.3) transparent;
      }
      
      /* Custom scrollbar */
      #sidebar::-webkit-scrollbar {
        width: 6px;
      }
      
      #sidebar::-webkit-scrollbar-track {
        background: transparent;
      }
      
      #sidebar::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.3);
        border-radius: 3px;
      }
      
      #sidebar::-webkit-scrollbar-thumb:hover {
        background: rgba(255,255,255,0.5);
      }
      
      /* Navigation Links */
      .main-nav ul {
        list-style: none;
        padding: 20px 0;
      }
      
      .main-nav a {
        display: flex;
        align-items: center;
        padding: 12px 25px;
        color: var(--text-light);
        text-decoration: none;
        transition: all var(--transition-speed) ease;
        font-size: 0.95rem;
      }
      
      .main-nav a:hover {
        background: rgba(255,255,255,0.1);
        transform: translateX(5px);
      }
      
      .main-nav a.active {
        background: rgba(255,255,255,0.15);
        font-weight: 500;
      }
      
      .main-nav a::before {
        content: '';
        position: absolute;
        left: 0;
        height: 20px;
        width: 3px;
        background: var(--text-light);
        opacity: 0;
        transition: opacity var(--transition-speed);
      }
      
      .main-nav a:hover::before,
      .main-nav a.active::before {
        opacity: 1;
      }
      
      /* Main Content */
      #mainContent {
        margin-left: var(--sidebar-width);
        margin-top: var(--header-height);
        padding: 30px;
        min-height: calc(100vh - var(--header-height));
        transition: margin-left var(--transition-speed) ease;
        background: #f8f9fa;
      }
      
      /* Hamburger Menu */
      .hamburger {
        display: none;
        cursor: pointer;
        padding: 15px;
        z-index: 1001;
      }
      
      .hamburger div {
        width: 25px;
        height: 2px;
        background: #333;
        margin: 5px 0;
        transition: all var(--transition-speed) ease;
      }
      
      /* Responsive Behavior */
      @media (max-width: 992px) {
        .hamburger {
          display: block;
        }
        
        #sidebar {
          transform: translateX(-100%);
        }
        
        #sidebar.open {
          transform: translateX(0);
        }
        
        #mainContent {
          margin-left: 0;
        }
        
        .hamburger.open div:nth-child(1) {
          transform: rotate(-45deg) translate(-5px, 6px);
        }
        
        .hamburger.open div:nth-child(2) {
          opacity: 0;
        }
        
        .hamburger.open div:nth-child(3) {
          transform: rotate(45deg) translate(-5px, -6px);
        }
      }
    `;

    // HTML Structure
    shadowRoot.innerHTML = `
      <!-- Top Navigation Bar -->
      <nav id="navTop">
        <div id="plusLogo">
          <img src="/images/plus-logo.png" alt="PLUS HIGHWAYS SDN. BHD.">
        </div>
        
        <div class="hamburger" id="hamburger">
          <div></div>
          <div></div>
          <div></div>
        </div>
        
        <div id="myProfile">
          <img src="/images/profile-icon.png" alt="My Profile">
        </div>
      </nav>
      
      <!-- Sidebar -->
      <div class="sidebar" id="sidebar">
        <nav class="main-nav">
          <ul>
            <li><a href="#" class="active"><i class="bi bi-speedometer2"></i> &nbsp; Dashboard</a></li>
            <li><a href="#"><i class="bi bi-people"></i> &nbsp; User Management</a></li>
            <li><a href="#"><i class="bi bi-cash-coin"></i> &nbsp; Toll Rates</a></li>
            <li><a href="#"><i class="bi bi-car-front"></i> &nbsp; License Plate Entry/Exit</a></li>
            <li><a href="#"><i class="bi bi-camera-video"></i> &nbsp; CCTV Streaming</a></li>
            <li><a href="#"><i class="bi bi-cloud-sun"></i> &nbsp; Weather Data</a></li>
            <li><a href="#"><i class="bi bi-exclamation-triangle"></i> &nbsp; Emergency Alerts</a></li>
            <li><a href="#"><i class="bi bi-cone-striped"></i> &nbsp; Congestion Alerts</a></li>
            <li><a href="#"><i class="bi bi-life-preserver"></i> &nbsp; SOS Emergency</a></li>
            <li><a href="#"><i class="bi bi-shield-check"></i> &nbsp; Vehicle Verifications</a></li>
            <li><a href="#"><i class="bi bi-chat-left-text"></i> &nbsp; Inquiry Reply</a></li>
          </ul>
        </nav>
      </div>
      
      <!-- Main Content Area -->
      <div class="main-content" id="mainContent">
        <header>
          <h1>Admin Portal</h1>
        </header>
        <main>
          <slot></slot>
        </main>
        <footer>
          <p>Copyright © ${new Date().getFullYear()} PLUS HIGHWAYS SDN. BHD.</p>
        </footer>
      </div>
    `;

    shadowRoot.prepend(style);

    // Add Bootstrap Icons
    const icons = document.createElement('link');
    icons.rel = 'stylesheet';
    icons.href = 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css';
    shadowRoot.prepend(icons);

    // Toggle functionality
    const hamburger = shadowRoot.getElementById('hamburger');
    const sidebar = shadowRoot.getElementById('sidebar');

    hamburger.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      hamburger.classList.toggle('open');
    });

    // Handle window resize
    window.addEventListener('resize', () => {
      if (window.innerWidth >= 992) {
        sidebar.classList.remove('open');
        hamburger.classList.remove('open');
      }
    });
  }
}

customElements.define('master-layout', MasterLayout);