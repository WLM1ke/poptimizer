<script>
	import { page } from '$app/stores';
</script>

<h1>{$page.url.pathname} {$page.status}: {$page.error.message}</h1>
