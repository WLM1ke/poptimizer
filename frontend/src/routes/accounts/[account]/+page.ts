import { AccountView } from "$lib/state/portfolio.svelte";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ params }) => {
	return { account: new AccountView(params.account) };
};
