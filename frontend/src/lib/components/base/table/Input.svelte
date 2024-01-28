<script lang="ts">
	export let value: number;
	export let step: number = 1;
</script>

<td>
	<input
		bind:value
		on:change
		class="border-bg-accent bg-bg-main w-32 rounded-md border p-1 text-right font-mono"
		type="number"
		{step}
		min="0"
	/>
</td>
