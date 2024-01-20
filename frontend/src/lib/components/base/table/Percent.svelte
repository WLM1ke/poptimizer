<script lang="ts">
	export let value: number;
	export let fractionDigits: number | undefined = 1;
</script>

<td class="text-right">
	{value.toLocaleString(undefined, {
		style: "percent",
		minimumFractionDigits: fractionDigits,
		maximumFractionDigits: fractionDigits
	})}
</td>
