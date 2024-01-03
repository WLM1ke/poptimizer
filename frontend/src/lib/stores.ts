import { page } from '$app/stores';
import type { Page } from '@sveltejs/kit';
import { derived } from 'svelte/store';

export const pageTitle = derived(page, (page: Page<Record<string, string>, string | null>) => {
	const path = page.url.pathname;
	const lastSlash = path.lastIndexOf('/');
	return path[lastSlash + 1].toUpperCase() + path.substring(lastSlash + 2);
});
