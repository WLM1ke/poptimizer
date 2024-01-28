<script lang="ts">
	export let value: number;
	export let step: number = 1;
</script>

<td>
	<input
		bind:value
		on:change
		class="w-32 rounded-md border border-bg-accent bg-bg-main p-1 text-right font-mono"
		type="number"
		{step}
		min="0"
	/>
</td>
