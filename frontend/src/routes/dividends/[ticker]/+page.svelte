<script lang="ts">
	import {
		Table,
		TableHead,
		TableHeadCell,
		TableBody,
		TableRow,
		TextCell,
		TableNumberCell,
		TableDayCell
	} from "$lib/components/base/table";
	export let data;
</script>

<Table>
	<TableHead>
		<TableHeadCell>Day</TableHeadCell>
		<TableHeadCell>Dividend</TableHeadCell>
		<TableHeadCell>Currency</TableHeadCell>
		<TableHeadCell>Status</TableHeadCell>
	</TableHead>
	<TableBody>
		{#each data.dividends as dividend ([dividend.day.toISOString(), dividend.dividend, dividend.currency])}
			<TableRow>
				<TableDayCell day={dividend.day} />
				<TableNumberCell value={dividend.dividend} />
				<TextCell text={dividend.currency} center={true} />
				<TextCell text={dividend.status} center={true} />
			</TableRow>
		{/each}
	</TableBody>
</Table>
