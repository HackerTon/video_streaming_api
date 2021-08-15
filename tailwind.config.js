module.exports = {
  mode: "jit",
  purge: [
    "./public/**/*.html",
    "./src/**/*.{js,jsx,ts,tsx,vue}",
    "./templates/*.html",
  ],
  darkMode: false, // or 'media' or 'class'
  theme: {
    extend: {
      fontFamily: {
        poppins: ["Poppins", "sans-serif"],
      },
      padding: {
        "1/3": "33.33333%",
        "2/3": "66.66667%",
      },
    },
  },
  variants: {
    extend: {},
  },
  plugins: [],
};
