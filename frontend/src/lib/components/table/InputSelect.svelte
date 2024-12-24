<script lang="ts">
	let { onchange, options, value }: { onchange: () => void; options: string[]; value: string } = $props();
</script>

<td>
	<select
		bind:value
		{onchange}
		class="option_text border-bg-accent bg-bg-main w-32 appearance-none rounded-md border p-1 font-mono"
	>
		{#each options as option, index (index)}
			<option value={option}>
				{option}
			</option>
		{/each}
	</select>
</td>

<style>
	.option_text {
		text-align-last: center;
	}
</style>
