<svelte:options runes />

<script lang="ts">
	import H2 from "$lib/components/H2.svelte";
	import Switch from "$lib/components/Switch.svelte";
	import { portSortByValue } from "$lib/state/settings.svelte";
</script>

<section>
	<H2 text="Portfolio" />
	<ul class="pt-2">
		<li>
			<Switch label="sort value descending" checked={portSortByValue.value} onchange={portSortByValue.toggle} />
		</li>
	</ul>
</section>
