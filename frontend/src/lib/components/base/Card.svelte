<script lang="ts">
	import H2 from "$lib/components/base/H2.svelte";
</script>

<section class="bg-bg-accent max-w-max rounded-lg p-4">
	<div class="text-text-muted italic">
		<slot name="header" />
	</div>
	<H2>
		<slot name="main" />
	</H2>
	<div class="text-text-muted italic">
		<slot name="footer" />
	</div>
</section>
