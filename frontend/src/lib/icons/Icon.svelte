<script lang="ts">
	let { height = 'h-5', viewBox = '0 0 16 16', fill = 'fill-current' } = $props();
</script>

<svg xmlns="http://www.w3.org/2000/svg" class="{height} {fill}" {viewBox}>
	<slot />
</svg>
