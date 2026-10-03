import { atom } from "jotai";
import type { Contract } from "../motion-contract";
export type Pilot = {
  contract: Contract;
  baselineSha256: string;
  run: string;
  proof: { engine: { version: string; commit: string } };
};
export const pilotAtom = atom<Pilot | null>(null);
export const contractAtom = atom<Contract | null>(null);
export const motionDirtyAtom = atom(false);
