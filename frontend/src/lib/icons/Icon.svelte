<script lang="ts">
	export let height = "h-5";
	export let viewBox = "0 0 16 16";
	export let fill = "fill-current";
</script>

<svg xmlns="http://www.w3.org/2000/svg" class="{height} {fill}" {viewBox}>
	<slot />
</svg>
