import type { PageLoad } from "./$types";

export const load = (async () => {
	throw new Error("Some strange error");
}) satisfies PageLoad;
