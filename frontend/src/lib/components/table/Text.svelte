<script lang="ts">
	let { text, center = false, fixedWidth = true }: { text: string; center?: boolean; fixedWidth?: boolean } = $props();
</script>

<td class="p-2 font-mono" class:text-center={center} class:w-32={fixedWidth}>
	{text}
</td>
