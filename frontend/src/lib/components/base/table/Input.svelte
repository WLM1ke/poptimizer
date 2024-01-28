<script lang="ts">
	export let value: number;
</script>

<td>
	<input
		bind:value
		on:change
		class="border-bg-accent bg-bg-main w-32 rounded-md border p-1 text-right font-mono"
		type="number"
	/>
</td>
