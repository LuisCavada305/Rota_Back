module.exports = {
  presets: [
    ["@babel/preset-env", { targets: "defaults" }],
    "@babel/preset-react",
    "@babel/preset-typescript"
  ],
  plugins: [
    // Só se realmente for usar decorators
    ["@babel/plugin-proposal-decorators", { legacy: true }]
  ]
};
