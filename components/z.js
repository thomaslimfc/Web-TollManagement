class MasterLayout extends HTMLElement {
  constructor() {
    super();
    // 1. Create Shadow DOM with open mode (accessible from JS)
    const shadowRoot = this.attachShadow({ mode: 'open' });

    // 2. Create CSS link element
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = new URL('./master-layout.css', import.meta.url).href; // Proper path resolution

    // 3. Add fallback styles (prevents FOUC - Flash of Unstyled Content)
    const fallbackStyles = document.createElement('style');
    fallbackStyles.textContent = `
      :host {
        display: block;
        font-family: Arial, sans-serif;
      }

    `;

    // 4. Build HTML structure
    shadowRoot.innerHTML = `

      <nav id="navTop">
        <div class="hamburger" id="hamburger">
          <div></div>
          <div></div>
          <div></div>
        </div>

        <div id="plusLogo">
          <img src="/images/plus-logo.png" alt="PLUS HIGHWAYS SDN. BHD.">
        </div>
        <div id="myProfile">
          <img src="/images/profile-icon.png" alt="My Profile">
        </div>
      </nav>

      <div class="sidebar" id="sidebar">
        <nav class="main-nav">
          <ul>
            <li><a href="/">User Management</a></li>
            <li><a href="/">Toll Rates</a></li>
            <li><a href="/">License Plate Entry / Exit</a></li>
            <li><a href="/">CCTV Streaming</a></li>
            <li><a href="/">Weather Data</a></li>
            <li><a href="/">Emergency Alerts</a></li>
            <li><a href="/">Congestion Alerts</a></li>
            <li><a href="/">SOS Emergency Assistance</a></li>
            <li><a href="/">Vehicle Verifications</a></li>
            <li><a href="/">Inquiry Reply</a></li>            
          </ul>
        </nav>
      </div>

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

    // 5. Inject styles (fallback first, then external)
    shadowRoot.prepend(fallbackStyles);
    shadowRoot.prepend(link);

    // Toggle functionality
    const hamburger = shadowRoot.getElementById('hamburger');
    const sidebar = shadowRoot.getElementById('sidebar');

    hamburger.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      this._animateHamburger(hamburger, sidebar.classList.contains('open'));
    });

    link.onerror = () => {
      console.error('Failed to load stylesheet, using fallback styles');
      fallbackStyles.textContent += `
        #sidebar {
          background: #003366;
          color: white;
        }
        .main-nav a {
          color: white;
          padding: 12px;
          display: block;
        }
      `;
    };
  }

  _animateHamburger(hamburger, isOpen) {
    const bars = hamburger.querySelectorAll('div');
    bars[0].style.transform = isOpen ? 'rotate(-45deg) translate(-5px, 6px)' : '';
    bars[1].style.opacity = isOpen ? '0' : '1';
    bars[2].style.transform = isOpen ? 'rotate(45deg) translate(-5px, -6px)' : '';
  }
}

// 7. Register the component
customElements.define('master-layout', MasterLayout);

