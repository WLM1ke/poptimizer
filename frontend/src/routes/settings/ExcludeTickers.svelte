<script lang="ts">
	import H2 from "$lib/components/H2.svelte";
	import Delete from "$lib/icons/Delete.svelte";
	import Add from "$lib/icons/Add.svelte";
	import { scale } from "svelte/transition";
	import { flip } from "svelte/animate";
	import { excludeTickers } from "$lib/state/portfolio.svelte";

	let ticker = $state("");
	let inputRef: HTMLElement;
</script>

<section class="mt-4">
	<H2 text="Exclude Tickers" />
	<ul class="max-w-max">
		{#each excludeTickers.tickers as ticker (ticker)}
			<li transition:scale animate:flip class="flex items-center justify-between gap-2 pt-2">
				{ticker}
				<button onclick={() => excludeTickers.notExclude(ticker)} class="hover:text-link-hover">
					<Delete />
				</button>
			</li>
		{/each}
		<li class="flex items-center justify-between gap-2 pt-2">
			<input
				bind:this={inputRef}
				onkeydown={(event) => {
					if (event.key === "Enter") {
						excludeTickers.exclude(ticker);
						ticker = "";
					}
				}}
				class="rounded-md border border-bg-accent bg-bg-main p-1"
				bind:value={ticker}
				type="text"
				placeholder="Enter ticker to exclude"
			/>
			<button
				onclick={() => {
					excludeTickers.exclude(ticker);
					inputRef.focus();
					ticker = "";
				}}
				class="hover:text-link-hover"
			>
				<Add />
			</button>
		</li>
	</ul>
</section>
