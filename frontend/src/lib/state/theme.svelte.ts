import { PersistentState } from "./persistent.svelte";

export const theme = new PersistentState<"system" | "light" | "dark">("theme", "system");
