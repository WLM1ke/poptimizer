import { addAlert } from "$lib/components/alerts";

const request = async (
	url: string,
	method: "GET" | "POST" | "PUT" | "DELETE",
	body: object | undefined = undefined
) => {
	try {
		const res = await fetch(url, { method, body: JSON.stringify(body) });
		if (!res.ok) {
			throw new Error(await res.text());
		}

		return await res.json();
	} catch (err) {
		let msg: string;

		if (err instanceof Error) {
			msg = err.message;
		} else {
			msg = JSON.stringify(err);
		}
		addAlert(msg);

		return null;
	}
};

export const get = async (url: string) => {
	return await request(url, "GET");
};

export const post = async (url: string, body: object | undefined = undefined) => {
	return await request(url, "POST", body);
};

export const put = async (url: string, body: object | undefined = undefined) => {
	return await request(url, "PUT", body);
};

export const del = async (url: string) => {
	return await request(url, "DELETE");
};
