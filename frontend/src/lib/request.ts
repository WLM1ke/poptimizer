import { invalidate } from "$app/navigation";
import { alerts } from "$lib/state/alerts.svelte";
import { error, redirect } from "@sveltejs/kit";

const request = async (
	fetchFn: typeof fetch,
	url: string,
	method: "GET" | "POST" | "PUT" | "DELETE",
	body: object | undefined = undefined
) => {
	try {
		const res = await fetchFn(url, { method, body: JSON.stringify(body) });
		if (!res.ok) {
			throw new Error(await res.text());
		}
		if (res.status === 204) {
			return null;
		}

		return await res.json();
	} catch (err) {
		let msg: string;

		if (err instanceof Error) {
			msg = err.message;
		} else {
			msg = JSON.stringify(err);
		}
		alerts.addAlert(`${msg}`);

		setTimeout(() => invalidate("/api/dividends"), retryDelay);

		return undefined;
	}
};

export const get = async (fetchFn: typeof fetch, url: string) => {
	return await request(fetchFn, url, "GET");
};

export const post = async (fetchFn: typeof fetch, url: string, body: object | undefined = undefined) => {
	return await request(fetchFn, url, "POST", body);
};

export const put = async (fetchFn: typeof fetch, url: string, body: object | undefined = undefined) => {
	return await request(fetchFn, url, "PUT", body);
};

export const del = async (fetchFn: typeof fetch, url: string) => {
	return await request(fetchFn, url, "DELETE");
};
