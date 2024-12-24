<script lang="ts">
	let { value = $bindable(), onchange }: { value: string; onchange?: () => void } = $props();
</script>

<td>
	<input bind:value {onchange} class="border-bg-accent bg-bg-main w-32 rounded-md border p-1 font-mono" type="text" />
</td>
