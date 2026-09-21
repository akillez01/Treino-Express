"use client";

import { useEffect, useState } from "react";
import SpotifySdkPlayer from "./SpotifySdkPlayer";
import { lerSelecaoSpotify, type SpotifySelection } from "../jukebox/SpotifyPlayer";

const SELECTION_EVENT = "treino-express:spotify-selection";

export default function SpotifyGlobalPlayer() {
  const [selection, setSelection] = useState<SpotifySelection | null>(null);

  useEffect(() => {
    setSelection(lerSelecaoSpotify());
    const atualizar = (event: Event) => {
      const detail = (event as CustomEvent<SpotifySelection>).detail;
      if (detail?.id) setSelection(detail);
    };
    window.addEventListener(SELECTION_EVENT, atualizar);
    return () => window.removeEventListener(SELECTION_EVENT, atualizar);
  }, []);

  return <SpotifySdkPlayer selection={selection} />;
}
