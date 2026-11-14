<script>
  // Les autres possibilités pour un bloc, avec leur date, leur portée et le drapeau « sensible ».
  // Si la page du bloc déborde, `tient(f)` dit si la proposition ferait tenir la page : en vert et en tête.
  import TriangleAlert from '@lucide/svelte/icons/triangle-alert'
  import Check from '@lucide/svelte/icons/check'
  import { dateCourte, PORTEES } from '$lib/format.js'
  let { liste = [], choisis = [], onchoisir, onfermer, tient = null } = $props()
  let filtre = $state('')
  let voirSensibles = $state(false)
  const filtres = $derived(liste.filter((f) => (voirSensibles || !f.sensible?.length)
    && (!filtre || (f.texte + ' ' + f.rubrique).toLowerCase().includes(filtre.toLowerCase()))))
  const place = $derived(tient ? new Map(filtres.map((f) => [f.id, choisis.includes(f.id) ? false : tient(f)])) : new Map())
  const enDefaut = $derived(!!tient && filtres.some((f) => tient(f) !== null))
  const visibles = $derived(enDefaut ? [...filtres].sort((a, b) => (place.get(b.id) ? 1 : 0) - (place.get(a.id) ? 1 : 0)) : filtres)
  const nbTiennent = $derived([...place.values()].filter(Boolean).length)
  const nbSensibles = $derived(liste.filter((f) => f.sensible?.length).length)
</script>

<div class="mt-3 rounded-xl border bg-background p-3">
  <div class="mb-2 flex flex-wrap items-center gap-2">
    <input bind:value={filtre} placeholder="Chercher…" class="h-9 flex-1 rounded-lg border bg-card px-3 text-sm" />
    {#if nbSensibles}
      <label class="flex items-center gap-1.5 text-xs text-muted-foreground">
        <input type="checkbox" bind:checked={voirSensibles} /> voir les {nbSensibles} sensibles
      </label>
    {/if}
    <button type="button" class="text-xs text-muted-foreground underline" onclick={onfermer}>fermer</button>
  </div>
  {#if enDefaut}
    <p class="mb-2 text-xs {nbTiennent ? 'text-valide' : 'text-muted-foreground'}">
      {nbTiennent ? `En vert : ${nbTiennent} proposition${nbTiennent > 1 ? 's' : ''} qui ferai${nbTiennent > 1 ? 'en' : ''}t tenir la page.` : "Aucune proposition ne fait tenir la page à elle seule : raccourcis aussi un autre bloc."}
    </p>
  {/if}
  <ul class="grid max-h-80 gap-1 overflow-y-auto">
    {#each visibles as f (f.id)}
      <li>
        <button type="button" onclick={() => onchoisir(f)} disabled={choisis.includes(f.id)}
                class="w-full rounded-lg px-2 py-1.5 text-left text-sm hover:bg-secondary disabled:opacity-40
                       {place.get(f.id) ? 'border border-valide/70 bg-valide/10' : ''}">
          <span class="text-xs text-muted-foreground">{dateCourte(f.date)} · {PORTEES[f.portee] ?? f.portee}
            {#if f.source === 'larousse'} · Larousse{/if}{#if f.langue === 'en'} · <b class="text-primary">en anglais, à traduire</b>{/if}</span>
          {#if f.sensible?.length}
            <span class="ml-1 inline-flex items-center gap-1 text-xs text-destructive"><TriangleAlert class="size-3" aria-hidden="true" />sensible : {f.sensible.join(', ')}</span>
          {/if}
          {#if place.get(f.id)}
            <span class="ml-1 inline-flex items-center gap-1 text-xs text-valide"><Check class="size-3" aria-hidden="true" />tient dans la place · {(f.rubrique?.length ?? 0) + f.texte.length} signes</span>
          {:else if enDefaut}
            <span class="ml-1 text-xs text-muted-foreground">· {(f.rubrique?.length ?? 0) + f.texte.length} signes</span>
          {/if}
          <span class="block">{#if f.rubrique}<b>{f.rubrique}.</b> {/if}{f.texte}</span>
        </button>
      </li>
    {:else}
      <li class="px-2 py-1.5 text-sm text-muted-foreground">Rien d'autre.</li>
    {/each}
  </ul>
</div>
