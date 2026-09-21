import SpotifyGlobalPlayer from "./_components/SpotifyGlobalPlayer";

export default function AlunoLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <SpotifyGlobalPlayer />
      {children}
    </>
  );
}
