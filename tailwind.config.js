module.exports = {
  content: [
    './app/templates/**/*.html',
    './app/static/js/**/*.js'
  ],
  theme: {
    extend: {
      colors: {
        blue: {
          900: '#001f3f',
          800: '#002b5c',
          700: '#003b6f',
          600: '#004c89',
          500: '#004080'
        },
        dark: {
          900: '#1a1a2e',
          800: '#212033',
          700: '#292b40',
          600: '#444',
          500: '#332f45'
        },
        light: {
          900: '#f8f9fa',
          800: '#ffffff',
          700: '#e9ecef',
          600: '#ced4da',
          500: '#dee2e6',
          400: '#212529'
        }
      },
      fontFamily: {
        mono: ['Courier New', 'monospace'],
        sans: ['Arial', 'Helvetica', 'sans-serif'],
        serif: ['Georgia', 'Times New Roman', 'serif']
      },
      borderRadius: {
        xl: '1rem'
      }
    }
  },
  plugins: []
};
