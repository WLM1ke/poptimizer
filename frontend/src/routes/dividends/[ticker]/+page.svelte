<script lang="ts">
	import {
		Table,
		TableHead,
		HeadCell,
		TableBody,
		TableRow,
		TextCell,
		NumberCell,
		AddCell,
		DeleteCell,
		InputCell,
		InputTextCell
	} from "$lib/components/table";
	import Button from "$lib/components/Button.svelte";
	import { addAlert } from "$lib/components/alerts";
	import { invalidate } from "$app/navigation";
	import { put } from "$lib/request.js";

	export let data;

	let ticker: string;
	let day: string;
	let dividend: number;
	let maxFractionDigits: number;

	$: {
		if (ticker != data.ticker) {
			ticker = data.ticker;
			day = data.dividends[data.dividends.length - 1].day;
			dividend = data.dividends[data.dividends.length - 1].dividend;
			maxFractionDigits = Math.max(...data.dividends.map((currentValue) => fractionDigits(currentValue.dividend)));
		}
	}

	const fractionDigits = (num: number) => {
		const numString = num.toString();
		const pointPos = numString.indexOf(".");

		if (pointPos === -1) {
			return 0;
		}

		return numString.length - pointPos - 1;
	};

	const toggleRow = (index: number) => {
		switch (data.dividends[index].status) {
			case "extra":
				data.dividends[index].status = "missed";
				break;
			case "missed":
				data.dividends[index].status = "extra";
		}
	};
	const addRow = () => {
		if (typeof dividend !== "number") {
			addAlert("Dividend should be number");
			return;
		}
		const date = new Date(day);
		if (date.toString() === "Invalid Date") {
			addAlert("Invalid Date");
			return;
		}
		data.dividends = [
			...data.dividends,
			{
				day: date.toISOString().slice(0, 10),
				dividend: dividend,
				status: "extra"
			}
		];
	};
	const save = async () => {
		await put(fetch, `/api/dividends/${data.ticker}`, {
			dividends: data.dividends
				.filter(({ status }) => {
					return status === "ok" || status === "extra";
				})
				.map(({ day, dividend }) => {
					return { day, dividend };
				})
				.toSorted((a, b) => {
					return a.day !== b.day ? a.day.localeCompare(b.day) : a.dividend - b.dividend;
				})
		});
		await invalidate((url) => url.pathname.startsWith("/api/dividends"));
	};
</script>

<Table>
	<TableHead>
		<HeadCell>Day</HeadCell>
		<HeadCell>Dividend</HeadCell>
		<HeadCell>Status</HeadCell>
	</TableHead>
	<TableBody>
		{#each data.dividends as dividend, index (index)}
			{#if dividend.status === "ok"}
				<TableRow>
					<TextCell text={dividend.day} />
					<NumberCell value={dividend.dividend} fractionDigits={maxFractionDigits} />
					<TextCell text="OK" center={true} />
				</TableRow>
			{:else if dividend.status === "extra"}
				<TableRow>
					<TextCell text={dividend.day} />
					<NumberCell value={dividend.dividend} fractionDigits={maxFractionDigits} />
					<DeleteCell on:click={() => toggleRow(index)} />
				</TableRow>
			{:else if dividend.status === "missed"}
				<TableRow muted>
					<TextCell text={dividend.day} />
					<NumberCell value={dividend.dividend} fractionDigits={maxFractionDigits} />
					<AddCell on:click={() => toggleRow(index)} />
				</TableRow>
			{/if}
		{/each}
		<TableRow muted>
			<InputTextCell bind:value={day} />
			<InputCell bind:value={dividend} />
			<AddCell on:click={() => addRow()} />
		</TableRow>
	</TableBody>
</Table>
<Button label="Save" on:click={save} />
