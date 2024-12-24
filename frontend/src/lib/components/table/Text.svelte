<script lang="ts">
	let { text, center = false }: { text: string; center?: boolean } = $props();
</script>

<td class="w-32 p-2 font-mono" class:text-center={center}>
	{text}
</td>
