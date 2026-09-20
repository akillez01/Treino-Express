import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    // QR Codes antigos da jukebox apontavam para /jukebox.
    return [{ source: "/jukebox", destination: "/aluno/jukebox", permanent: false }];
  },
};

export default nextConfig;
