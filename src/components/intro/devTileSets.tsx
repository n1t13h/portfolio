import type { ReactNode } from "react";
import {
  AgenticAiTile,
  MicroservicesTile,
  PostgresTile,
  PythonTile,
  ServerlessTile,
  SolidityTile,
  TemporalTile,
  TypeScriptTile,
  Web3Tile,
} from "./devTiles";

/** Index-aligned with the intro's floating tiles (9). */
export const DEV_FLOAT_TILES: ReactNode[] = [
  <TemporalTile key="temporal" />,
  <AgenticAiTile key="ai" />,
  <Web3Tile key="web3" />,
  <PythonTile key="python" />,
  <MicroservicesTile key="micro" />,
  <TypeScriptTile key="ts" />,
  <ServerlessTile key="serverless" />,
  <PostgresTile key="postgres" />,
  <SolidityTile key="solidity" />,
];

/** Cycled inside the wordmark window. */
export const DEV_WINDOW_TILES: ReactNode[] = [
  <TemporalTile key="temporal" />,
  <AgenticAiTile key="ai" />,
  <Web3Tile key="web3" />,
  <PythonTile key="python" />,
  <MicroservicesTile key="micro" />,
];
