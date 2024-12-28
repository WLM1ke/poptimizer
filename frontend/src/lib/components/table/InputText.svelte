<script lang="ts">
	let { value = $bindable(), onchange }: { value: string; onchange?: () => void } = $props();
</script>

<td>
	<input bind:value {onchange} class="w-32 rounded-md border border-bg-accent bg-bg-main p-1 font-mono" type="text" />
</td>
