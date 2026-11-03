/** @type {import('next').NextConfig} */
const nextConfig = {
  // Strict mode double-runs effects in dev, which would fire every API call twice.
  // Turned off so dev behaves exactly like the original single-page site.
  reactStrictMode: false,
  // Hide the floating "N" dev badge so `npm run dev` looks exactly like the original site.
  devIndicators: false,
};

module.exports = nextConfig;
