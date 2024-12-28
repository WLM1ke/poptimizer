<script lang="ts">
	interface FormEvent {
		target: EventTarget | null;
	}
	let {
		value = $bindable(),
		step = 1,
		onchange
	}: { value: number; step?: number; onchange?: (event: FormEvent) => void } = $props();
</script>

<td>
	<input
		bind:value
		{onchange}
		class="w-32 rounded-md border border-bg-accent bg-bg-main p-1 text-right font-mono"
		type="number"
		{step}
		min="0"
	/>
</td>
