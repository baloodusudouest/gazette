<script>
  // 0.17 : un élément à relire (paragraphe, photo, rumeur, lettre…), avec ses quatre gestes, pareils dans la
  // Gazette et La Récidive : Valider (il disparaît), IA (propositions de l'IA du PC, en file si elle tourne déjà),
  // Changer (d'autres données : autre événement, autre photo, autre proposition…), Refuser (supprimé ; absent pour
  // un élément obligatoire). Un élément validé revient s'il change ou si sa page déborde à l'impression.
  import { getContext } from 'svelte'
  import Check from '@lucide/svelte/icons/check'
  import RefreshCw from '@lucide/svelte/icons/refresh-cw'
  import Sparkles from '@lucide/svelte/icons/sparkles'
  import X from '@lucide/svelte/icons/x'
  import { empreinte } from '$lib/validation.js'

  let { cle, page, valeur, titre, onia = null, onchanger = null, onrefuser = null, changer = 'Changer', children } = $props()
  const v = getContext('validation')
  const h = $derived(empreinte(valeur))
  const trop = $derived(v.trop(page))
  const valide = $derived(v.valides()[cle] === h && !trop)

  $effect(() => {
    v.registre[cle] = valide
    return () => { delete v.registre[cle] }
  })
</script>

{#if !valide || v.revoir()}
  <div role="group" aria-label={titre}
       class="grid min-w-0 gap-1 rounded-xl border p-2 {trop ? 'border-destructive/70' : ''} {valide ? 'border-valide/50 opacity-70' : ''}">
    <div class="flex min-w-0 items-center justify-between gap-2">
      <span class="truncate text-[0.7rem] font-medium tracking-wide text-muted-foreground uppercase">{titre}{trop ? ' · page trop pleine' : ''}</span>
      <span class="flex shrink-0 items-center gap-0.5">
        <button type="button" class="rounded-md p-1.5 hover:bg-valide/15 {valide ? 'text-valide' : 'text-muted-foreground hover:text-valide'}"
                aria-label="Valider : {titre}" title="Valider" onclick={() => v.valider(cle, h)}><Check class="size-4" aria-hidden="true" /></button>
        {#if onia}<button type="button" class="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
                          aria-label="IA : {titre}" title="L'IA propose (en file si elle tourne déjà)" onclick={onia}><Sparkles class="size-4" aria-hidden="true" /></button>{/if}
        {#if onchanger}<button type="button" class="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
                               aria-label="{changer} : {titre}" title={changer} onclick={onchanger}><RefreshCw class="size-4" aria-hidden="true" /></button>{/if}
        {#if onrefuser}<button type="button" class="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/15 hover:text-destructive"
                               aria-label="Refuser : {titre}" title="Refuser (supprimer)" onclick={onrefuser}><X class="size-4" aria-hidden="true" /></button>{/if}
      </span>
    </div>
    {@render children()}
  </div>
{/if}
