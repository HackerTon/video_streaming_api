module.exports = {
  mode: "jit",
  purge: ["./**/*.html", "./**/*.js"],
  darkMode: false, // or 'media' or 'class'
  theme: {
    extend: {
      animation: {
        wiggle: "wiggle 10.0s infinite",
      },
      keyframes: {
        wiggle: {
          "0%": { transform: "translateX(-50vw)" },
          "100%": { transform: "translateX(120vw)" },
        },
      },
    },
  },
  variants: {
    extend: {},
  },
  plugins: [],
};
