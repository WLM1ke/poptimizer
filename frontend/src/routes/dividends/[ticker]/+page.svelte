<script lang="ts">
	import {
		Table,
		TableRow,
		TextCell,
		NumberCell,
		AddCell,
		DeleteCell,
		InputCell,
		InputTextCell
	} from "$lib/components/table";
	import Button from "$lib/components/Button.svelte";
	import { type PageData } from "./$types";

	let { data }: { data: PageData } = $props();
	let dividends = $derived(data.dividends);
</script>

<Table headers={["Day", "Dividend", "Status"]}>
	{#snippet rows()}
		{#each dividends.dividends as dividend, index (index)}
			{#if dividend.status === "ok"}
				<TableRow>
					{#snippet cells()}
						<TextCell text={dividend.day} />
						<NumberCell value={dividend.dividend} fractionDigits={dividends.maxFractionDigits} />
						<TextCell text="OK" center={true} />
					{/snippet}
				</TableRow>
			{:else if dividend.status === "extra"}
				<TableRow>
					{#snippet cells()}
						<TextCell text={dividend.day} />
						<NumberCell value={dividend.dividend} fractionDigits={dividends.maxFractionDigits} />
						<DeleteCell onclick={() => dividends.toggleRow(index)} />
					{/snippet}
				</TableRow>
			{:else if dividend.status === "missed"}
				<TableRow muted>
					{#snippet cells()}
						<TextCell text={dividend.day} />
						<NumberCell value={dividend.dividend} fractionDigits={dividends.maxFractionDigits} />
						<AddCell onclick={() => dividends.toggleRow(index)} />
					{/snippet}
				</TableRow>
			{/if}
		{/each}
		<TableRow muted>
			{#snippet cells()}
				<InputTextCell bind:value={dividends.next.day} />
				<InputCell bind:value={dividends.next.dividend} />
				<AddCell onclick={() => dividends.addRow()} />
			{/snippet}
		</TableRow>
	{/snippet}
</Table>
<Button label="Save" onclick={dividends.update} />
