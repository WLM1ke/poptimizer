<script lang="ts">
	export let day: Date;
</script>

<td class="w-32 p-2 font-mono">
	{day.toISOString().slice(0, 10)}
</td>
