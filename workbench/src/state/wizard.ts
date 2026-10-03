import { atom } from "jotai";
import { atomWithStorage } from "jotai/utils";
import starter from "../../../recipes/motion-starter.json";
import { invalidate, restoreDraft } from "../lib/prompts.js";
export const defaults = {
  identity: starter.identity,
  style: "清晰线稿、柔和赛璐璐上色、可爱二次元",
  direction: "向右侧面",
  reference: "",
  actions: ["待机", "走路"],
  timing: starter.timing,
  cell: 256,
  display: 128,
  artifactKind: "auto",
  artifact: "",
  handoff: "",
  manifest: "",
  previewUrl: "",
  issues: "",
  exportTarget: "universal",
  project: "",
  bundle: "",
  integration: "",
};
export type Wizard = typeof defaults;
export function restoreWizard(saved: unknown): Wizard {
  if (!saved || typeof saved !== "object") return { ...defaults };
  const old = restoreDraft({ ...saved, version: 2 }) as unknown as Record<
    string,
    unknown
  >;
  const value = { ...defaults };
  for (const key of Object.keys(defaults) as (keyof Wizard)[]) {
    if (key === "cell" || key === "display") {
      const n = Number((saved as Record<string, unknown>)[key]);
      if (Number.isInteger(n) && n > 0 && n <= 2048) value[key] = n;
    } else if (key === "actions") {
      if (Array.isArray(old.actions)) value.actions = old.actions as string[];
    } else if (typeof old[key] === "string")
      Object.assign(value, { [key]: old[key] });
  }
  return value;
}
// 兼容旧流水线文本草稿；损坏或禁用的本机存储回退默认值，绝不恢复确认状态。
const storage = {
  getItem(key: string) {
    try {
      return restoreWizard(
        JSON.parse(
          localStorage.getItem(key) ||
            localStorage.getItem("motion-wizard-v2") ||
            "null",
        ),
      );
    } catch {
      return { ...defaults };
    }
  },
  setItem(key: string, value: Wizard) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* 存储不可用仍可继续当前会话。 */
    }
  },
  removeItem(key: string) {
    try {
      localStorage.removeItem(key);
    } catch {
      /* 不影响当前制作。 */
    }
  },
};
export const wizardAtom = atomWithStorage<Wizard>(
  "motion-react-draft-v1",
  defaults,
  storage,
  { getOnInit: true },
);
// 确认状态只在本次会话保存，旧草稿不能自动通过新素材的验收。
export const confirmedAtom = atom(false);
export const acceptedAtom = atom(false);
export const updateWizardAtom = atom(
  null,
  (get, set, patch: Partial<Wizard>) => {
    const fields = Object.keys(patch);
    set(wizardAtom, { ...get(wizardAtom), ...patch });
    if (fields.some((f) => invalidate(f).reference)) set(confirmedAtom, false);
    if (
      fields.some((f) => invalidate(f === "actions" ? "action" : f).acceptance)
    )
      set(acceptedAtom, false);
  },
);
