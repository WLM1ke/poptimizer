<script lang="ts">
	import {
		Table,
		TableHead,
		TableHeadCell,
		TableBody,
		TableRow,
		TextCell,
		TableNumberCell,
		TableDayCell,
		AddCell,
		DeleteCell
	} from "$lib/components/base/table";
	export let data;

	const toggleRow = (index: number) => {
		console.info(index);
		switch (data.dividends[index].status) {
			case "extra":
				data.dividends[index].status = "missed";
				break;
			case "missed":
				data.dividends[index].status = "extra";
		}
	};
</script>

<Table>
	<TableHead>
		<TableHeadCell>Day</TableHeadCell>
		<TableHeadCell>Dividend</TableHeadCell>
		<TableHeadCell>Currency</TableHeadCell>
		<TableHeadCell>Status</TableHeadCell>
	</TableHead>
	<TableBody>
		{#each data.dividends as dividend, index (index)}
			{#if dividend.status === "ok"}
				<TableRow>
					<TableDayCell day={dividend.day} />
					<TableNumberCell value={dividend.dividend} />
					<TextCell text={dividend.currency.toUpperCase()} center={true} />
					<TextCell text="OK" center={true} />
				</TableRow>
			{:else if dividend.status === "extra"}
				<TableRow>
					<TableDayCell day={dividend.day} />
					<TableNumberCell value={dividend.dividend} />
					<TextCell text={dividend.currency.toUpperCase()} center={true} />
					<DeleteCell on:click={() => toggleRow(index)} />
				</TableRow>
			{:else if dividend.status === "missed"}
				<TableRow muted>
					<TableDayCell day={dividend.day} />
					<TableNumberCell value={dividend.dividend} />
					<TextCell text={dividend.currency.toUpperCase()} center={true} />
					<AddCell on:click={() => toggleRow(index)} />
				</TableRow>
			{/if}
		{/each}
	</TableBody>
</Table>
