import type { LayoutLoad } from "./$types";
import { errors } from "$lib/stores";

export const ssr = false;
// https://github.com/sveltejs/kit/issues/11310#issuecomment-1856005354
export const load = (async ({ fetch }) => {
	try {
		const res = await fetch("/api/portfolio");
		if (res.ok) {
			return await res.json();
		}
		const msg = await res.text();
		errors.update((errs) => [...errs, msg]);
	} catch (err) {
		let msg: string;
		if (err instanceof Error) {
			msg = err.message;
		} else {
			msg = JSON.stringify(err);
		}
		errors.update((errs) => [...errs, msg]);
	}
}) satisfies LayoutLoad;
