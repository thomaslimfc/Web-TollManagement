// js/firebase_init.js

window.initializeFirebase = () => {
  return new Promise((resolve, reject) => {
    const firebaseConfig = {
      apiKey: "AIzaSyARgm74vYV7j2fFKETh_rjmMZEgTk5br10",
      authDomain: "plus-370c3.firebaseapp.com",
      projectId: "plus-370c3",
      storageBucket: "plus-370c3.appspot.com",
      messagingSenderId: "230901289680",
      appId: "1:230901289680:web:5fded638de55b9b27904d5"
    };

    // Load Firebase compatibility SDKs
    const scripts = [
      'https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js',
      'https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore-compat.js',
      'https://www.gstatic.com/firebasejs/10.12.0/firebase-auth-compat.js'
    ];

    let loaded = 0;

    scripts.forEach(src => {
      const script = document.createElement('script');
      script.src = src;
      script.onload = () => {
        loaded++;
        if (loaded === scripts.length) {
          // Initialize Firebase and Firestore once all scripts are loaded
          firebase.initializeApp(firebaseConfig);
          const db = firebase.firestore();
          resolve({ db });
        }
      };
      script.onerror = () => reject(`Failed to load ${src}`);
      document.head.appendChild(script);
    });
  });
};
