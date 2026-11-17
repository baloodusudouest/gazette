<script>
  // 0.12 : aides de l'IA du PC pour un bloc de la Gazette classique (titres, raccourcir, version journal, traduire,
  // mot des hôtes). Des propositions à choisir : un toucher les applique au bloc ; rien n'est enregistré sans Julien.
  // 0.14 : les propositions de chaque aide restent affichées ensemble ; `tout()` (bouton « IA » du haut de la page)
  // demande toutes les aides du bloc d'un coup.
  import Sparkles from '@lucide/svelte/icons/sparkles'
  import { api } from '$lib/api.js'
  import { enfiler } from '$lib/fileIa.svelte.js'

  let { pid, texte, actions, signes = null, onapply, nom = 'un bloc' } = $props()
  const NOMS = { titres: 'Titres', raccourcir: 'Raccourcir', journal: 'Version journal', traduire: 'Traduire', mot: '3 mots' }
  let res = $state({})            // {action: [propositions]}
  let attente = $state('')
  let erreur = $state('')

  // 0.17 : chaque demande passe par la file commune de l'IA (une à la fois, à la suite de celles en cours)
  async function demander(action) {
    attente = action
    erreur = ''
    try {
      const props = await enfiler(`${nom} (${NOMS[action].toLowerCase()})`, async () =>
        (await api.post(`/api/livrets/${pid}/ia`, { action, texte: texte(), signes: action === 'raccourcir' ? signes : null })).propositions)
      res = { ...res, [action]: props }
    } catch (err) { erreur = err.message }
    attente = ''
    return erreur
  }

  // Toutes les aides du bloc, une après l'autre (l'IA du PC traite une demande à la fois). « Traduire » seulement
  // pour un texte qui a l'air anglais ; rien pour un texte trop court (sauf le mot des hôtes).
  export async function tout() {
    const t = (texte() || '').trim()
    let faites = 0
    for (const a of actions) {
      if (a === 'traduire' && !/\b(the|and|of|was|were|is|in)\b/i.test(t)) continue
      if (a !== 'mot' && t.length < 10) continue
      const e = await demander(a)
      if (e) return { faites, erreur: e }
      faites++
    }
    return { faites, erreur: '' }
  }
  function appliquer(action, t) {
    onapply(action, t)
    const { [action]: _, ...reste } = res
    res = reste
  }
</script>

<div class="mt-1 grid min-w-0 gap-1">
  <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
    <Sparkles class="size-3.5" aria-hidden="true" /><span class="sr-only">IA :</span>
    {#each actions as a}
      <button type="button" class="hover:text-foreground disabled:opacity-50" disabled={attente === a} onclick={() => demander(a)}>
        {attente === a ? '…' : NOMS[a]}</button>
    {/each}
  </div>
  {#if erreur}<p class="text-xs text-destructive">{erreur}</p>{/if}
  {#each Object.entries(res) as [action, props] (action)}
    {#if props.length}
      <ul class="grid gap-1 rounded-lg border border-dashed p-1.5" aria-label="Propositions de l'IA : {NOMS[action]}">
        <li class="flex items-center justify-between px-2 text-[0.7rem] font-medium tracking-wide text-muted-foreground uppercase">
          {NOMS[action]}
          <button type="button" class="normal-case hover:text-foreground" onclick={() => { const { [action]: _, ...r } = res; res = r }}>Fermer</button></li>
        {#each props as t}
          <li><button type="button" class="w-full rounded-md px-2 py-1 text-left text-sm break-words whitespace-pre-line hover:bg-secondary"
                      onclick={() => appliquer(action, t)}>{t}</button></li>
        {/each}
      </ul>
    {/if}
  {/each}
</div>
