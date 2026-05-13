/** @type {import('next').NextConfig} */
const nextConfig = {
  // Backend API proxying is handled by app/api/[...path]/route.ts at request
  // time, so Docker runtime env is used instead of baking a build-time URL.
};

export default nextConfig;
