<script lang="ts">
	export let options: string[];
	export let value: string;
</script>

<td>
	<select
		bind:value
		on:change
		class="option_text w-32 appearance-none rounded-md border border-bg-accent bg-bg-main p-1 font-mono"
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
