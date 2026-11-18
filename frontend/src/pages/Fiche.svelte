<script>
  // 0.23 : la fiche complète d'une personne pour les journaux (Gazette et La Récidive), rangée dans carnet (≥ 2.33).
  // Toutes les rubriques en amorces repliables, avec des exemples à toucher ; chaque réponse est une « pépite »
  // (200 caractères au plus) écrite une par une dans carnet (contrôle `le` : 409 si elle a changé ailleurs).
  // En haut : la ligne « vrac » (rangée par mots-clés, modifiable), la jauge (nombre de pépites, paliers 5/15/30) et
  // ce qui est déjà connu (carnet, anciennes Récidives, étapes de Sillage) en suggestions grisées « Ajouter ».
  // « Sujets interdits » : à part, masqués par défaut, jamais envoyés à l'IA. Brouillon local tant qu'une écriture
  // n'a pas réussi. carnet absent, pas à jour ou personne introuvable : la page le dit, rien n'est écrit.
  import { onMount } from 'svelte'
  import ArrowLeft from '@lucide/svelte/icons/arrow-left'
  import Plus from '@lucide/svelte/icons/plus'
  import Trash2 from '@lucide/svelte/icons/trash-2'
  import Ban from '@lucide/svelte/icons/ban'
  import Pencil from '@lucide/svelte/icons/pencil'
  import Eye from '@lucide/svelte/icons/eye'
  import EyeOff from '@lucide/svelte/icons/eye-off'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'

  let { id, retour = '', ondeconnecte } = $props()
  let d = $state(null)
  let message = $state('')
  let erreur = $state('')
  let attente = $state(false)
  let vrac = $state('')
  let vracRubrique = $state('')       // rubrique proposée pour la ligne vrac (modifiable avant d'ajouter)
  let vracTouchee = $state(false)     // Julien a choisi la rubrique lui-même : on ne la devine plus
  let saisies = $state({})            // rubrique → texte en cours
  let edition = $state(null)          // {id, texte} : pépite en cours de modification
  let voirInterdits = $state(false)
  let minuteur = null

  const CLE_BROUILLON = `gazette-fiche-${id}`
  const ecriture = $derived(!!d?.etat?.ecriture)
  const titres = $derived(d ? Object.fromEntries([
    ...d.rubriques.familles.flatMap((f) => f.rubriques.map((r) => [r.cle, r.titre])),
    [d.rubriques.interdits.cle, d.rubriques.interdits.titre]]) : {})
  const choixRubriques = $derived(d ? [...d.rubriques.familles.flatMap((f) => f.rubriques.map((r) => ({ cle: r.cle, titre: `${f.titre} › ${r.titre}` }))),
                                       { cle: 'interdits', titre: 'Sujets interdits' }] : [])
  const interdits = $derived((d?.pepites ?? []).filter((p) => p.interdit || p.rubrique === 'interdits'))
  const de = (cle) => (d?.pepites ?? []).filter((p) => p.rubrique === cle && !p.interdit)
  const jauge = $derived(d?.jauge ?? { nombre: 0, palier: '', prochain: 5 })
  const largeurJauge = $derived(Math.min(100, Math.round((jauge.nombre / 30) * 100)))

  // ------------------------------------------------------------ brouillon local (localStorage, jamais bloquant)
  function lireBrouillon() {
    try {
      const b = JSON.parse(localStorage.getItem(CLE_BROUILLON) || '{}')
      if (b && typeof b === 'object') { saisies = b.saisies ?? {}; vrac = b.vrac ?? '' }
    } catch { /* stockage indisponible (navigation privée) : sans gravité */ }
  }
  function garderBrouillon() {
    try {
      const vides = !vrac.trim() && !Object.values(saisies).some((t) => (t ?? '').trim())
      if (vides) localStorage.removeItem(CLE_BROUILLON)
      else localStorage.setItem(CLE_BROUILLON, JSON.stringify({ saisies, vrac }))
    } catch { /* idem */ }
  }

  async function lire() {
    try {
      d = await api.get(`/api/fiches/${id}`)
      erreur = ''
    } catch (err) {
      if (err.statut === 401) ondeconnecte?.()
      else erreur = err.message
    }
  }

  async function ecrire(geste) {
    attente = true
    message = ''
    try {
      await geste()
      await lire()
      return true
    } catch (err) {
      if (err.statut === 401) ondeconnecte?.()
      message = err.message
      if (err.statut === 409 || err.statut === 404) await lire()      // changée ou effacée ailleurs : on relit
      return false
    } finally {
      attente = false
    }
  }

  async function ajouter(rubrique, texte, source = 'julien') {
    const t = (texte ?? '').trim()
    if (!t) return false
    return ecrire(async () => {
      const r = await api.post(`/api/fiches/${id}/pepites`, { rubrique, texte: t, source })
      message = r.pepite?.deja ? 'Déjà dans la fiche.' : `Ajouté dans « ${titres[r.pepite?.rubrique] ?? 'Autre'} ».`
    })
  }
  async function ajouterSaisie(cle) {
    if (await ajouter(cle, saisies[cle])) { saisies = { ...saisies, [cle]: '' }; garderBrouillon() }
  }
  async function ajouterVrac() {
    if (await ajouter(vracRubrique || 'vrac', vrac)) { vrac = ''; vracRubrique = ''; vracTouchee = false; garderBrouillon() }
  }
  const modifier = (p, champs) => ecrire(() => api.put(`/api/fiches/${id}/pepites/${p.id}`, { le: p.le, ...champs }))
  async function effacer(p) {
    if (!confirm(`Effacer « ${p.texte} » de la fiche ?`)) return
    await ecrire(() => api.del(`/api/fiches/${id}/pepites/${p.id}`, { le: p.le }))
  }
  async function enregistrerEdition(p) {
    if (await modifier(p, { texte: edition.texte })) edition = null
  }

  // la ligne vrac : rubrique devinée par mots-clés (côté serveur, sans IA), affichée avant d'ajouter
  function devinerVrac() {
    garderBrouillon()
    clearTimeout(minuteur)
    if (vracTouchee) return
    minuteur = setTimeout(async () => {
      if (!vrac.trim()) { vracRubrique = ''; return }
      try { vracRubrique = (await api.post('/api/fiches/ranger', { texte: vrac })).rubrique } catch { /* sans gravité */ }
    }, 250)
  }

  function revenir() {
    if (retour) location.hash = '#/' + retour
    else if (history.length > 1) history.back()
    else location.hash = '#/livrets'
  }

  onMount(() => { lireBrouillon(); lire() })
</script>

{#snippet pepite(p)}
  <li class="group grid min-w-0 gap-1 rounded-lg border bg-background/60 px-3 py-2 text-sm">
    {#if edition?.id === p.id}
      <textarea class="w-full min-w-0 rounded-md border bg-background px-2 py-1" rows="2" maxlength={d.maxi} bind:value={edition.texte}
                aria-label="Modifier la pépite"></textarea>
      <div class="flex flex-wrap justify-end gap-2">
        <Button size="sm" variant="ghost" onclick={() => (edition = null)}>Annuler</Button>
        <Button size="sm" onclick={() => enregistrerEdition(p)} disabled={attente || !edition.texte.trim()}>Enregistrer</Button>
      </div>
    {:else}
      <p class="break-words">{p.texte}</p>
      <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        {#if p.source !== 'julien'}<span>{p.source === 'recidive' ? 'ancienne Récidive' : p.source}</span>{/if}
        {#if p.parue_le}<span>parue le {p.parue_le.slice(8, 10)}/{p.parue_le.slice(5, 7)}/{p.parue_le.slice(0, 4)}</span>{/if}
        {#if ecriture}
          <button type="button" class="inline-flex items-center gap-1 hover:text-foreground" onclick={() => (edition = { id: p.id, texte: p.texte })}>
            <Pencil class="size-3" aria-hidden="true" />Modifier</button>
          <label class="inline-flex min-w-0 items-center gap-1">
            <span class="sr-only">Déplacer vers</span>
            <select class="max-w-[11rem] min-w-0 rounded-md border bg-background px-1 py-0.5 text-xs" value={p.rubrique}
                    onchange={(e) => modifier(p, { rubrique: e.currentTarget.value })} aria-label="Déplacer « {p.texte} »">
              {#each choixRubriques as r}<option value={r.cle}>{r.titre}</option>{/each}
            </select>
          </label>
          {#if !p.interdit}
            <button type="button" class="inline-flex items-center gap-1 hover:text-destructive" onclick={() => modifier(p, { rubrique: 'interdits' })}
                    title="Ranger dans les sujets interdits : jamais envoyé à l'IA"><Ban class="size-3" aria-hidden="true" />Interdire</button>
          {/if}
          <button type="button" class="inline-flex items-center gap-1 hover:text-destructive" onclick={() => effacer(p)}>
            <Trash2 class="size-3" aria-hidden="true" />Effacer</button>
        {/if}
      </div>
    {/if}
  </li>
{/snippet}

{#snippet saisie(cle, exemples, libelle)}
  {#if ecriture}
    {#if exemples?.length}
      <div class="flex flex-wrap gap-1.5" role="group" aria-label="Exemples pour {libelle}">
        {#each exemples as ex}
          <button type="button" class="rounded-full border border-dashed px-2.5 py-0.5 text-xs text-muted-foreground hover:border-foreground hover:text-foreground"
                  onclick={() => { saisies = { ...saisies, [cle]: ex }; garderBrouillon() }}>{ex}</button>
        {/each}
      </div>
    {/if}
    <div class="flex min-w-0 gap-2">
      <input class="w-full min-w-0 rounded-lg border bg-background px-2 py-1 text-sm" maxlength={d.maxi} value={saisies[cle] ?? ''}
             oninput={(e) => { saisies = { ...saisies, [cle]: e.currentTarget.value }; garderBrouillon() }}
             onkeydown={(e) => e.key === 'Enter' && ajouterSaisie(cle)}
             placeholder="Un détail, une histoire, une manie…" aria-label="Nouvelle pépite : {libelle}" />
      <Button size="sm" variant="outline" class="shrink-0" onclick={() => ajouterSaisie(cle)} disabled={attente || !(saisies[cle] ?? '').trim()}>
        <Plus class="size-3.5" aria-hidden="true" />Ajouter</Button>
    </div>
  {/if}
{/snippet}

<button type="button" onclick={revenir} class="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
  <ArrowLeft class="size-4" aria-hidden="true" /> Retour
</button>

{#if erreur}
  <p class="rounded-xl border border-destructive/60 px-4 py-2 text-sm text-destructive" role="alert">{erreur}</p>
{:else if d}
  <header class="mb-5">
    <p class="etiquette">Fiche complète · pour les journaux (non imprimé)</p>
    <h1 class="titre break-words">{d.personne.nom}</h1>
    <p class="mt-1 max-w-prose text-sm text-muted-foreground">
      Plus il y a de détails, plus l'IA du PC écrit juste : à chaque demande, elle en reçoit 3 à 5 tirés au hasard (d'abord ceux jamais parus), avec le ton souhaité.
      Rangé dans carnet, modifiable aussi depuis la fiche du contact.</p>
  </header>

  {#if d.etat.message}
    <p class="mb-4 rounded-xl border px-4 py-2 text-sm {d.etat.carnet === 'ok' ? '' : 'border-primary/60'}" role="status" aria-label="État de carnet">{d.etat.message}</p>
  {/if}
  {#if message}<p class="mb-4 rounded-xl border px-4 py-2 text-sm" role="status">{message}</p>{/if}

  {#if d.etat.carnet === 'ok' || d.pepites.length}
    <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
      <div class="grid min-w-0 content-start gap-4">
        <!-- la ligne vrac -->
        {#if ecriture}
          <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Vrac">
            <h2 class="etiquette mb-2">Vrac : un détail, rangé tout seul</h2>
            <div class="flex min-w-0 gap-2">
              <input class="w-full min-w-0 rounded-lg border bg-background px-3 py-1.5 text-sm" maxlength={d.maxi} bind:value={vrac} oninput={devinerVrac}
                     onkeydown={(e) => e.key === 'Enter' && ajouterVrac()} placeholder="Ex. : déteste les endives, ronfle comme un tracteur…" aria-label="Ligne vrac" />
              <Button size="sm" class="shrink-0" onclick={ajouterVrac} disabled={attente || !vrac.trim()}><Plus class="size-3.5" aria-hidden="true" />Ajouter</Button>
            </div>
            {#if vrac.trim()}
              <label class="mt-2 flex min-w-0 flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span>Rangé dans :</span>
                <select class="max-w-full min-w-0 rounded-md border bg-background px-1 py-0.5 text-xs" value={vracRubrique || 'autre'}
                        onchange={(e) => { vracRubrique = e.currentTarget.value; vracTouchee = true }} aria-label="Rubrique de la ligne vrac">
                  {#each choixRubriques as r}<option value={r.cle}>{r.titre}</option>{/each}
                </select>
              </label>
            {/if}
          </section>
        {/if}

        <!-- déjà connu : suggestions grisées, jamais recopiées sans « Ajouter » -->
        {#if d.suggestions.length}
          <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Déjà connu">
            <h2 class="etiquette mb-2">Déjà connu, à valider ({d.suggestions.length})</h2>
            <ul class="grid gap-1.5">
              {#each d.suggestions as s}
                <li class="flex min-w-0 items-start justify-between gap-2 rounded-lg border border-dashed px-3 py-1.5 text-sm text-muted-foreground">
                  <span class="min-w-0 break-words">{s.texte}
                    <span class="block text-xs">{titres[s.rubrique] ?? 'Autre'} · {s.origine ?? s.source}</span></span>
                  {#if ecriture}
                    <Button size="xs" variant="outline" class="shrink-0" onclick={() => ajouter(s.rubrique, s.texte, s.source)} disabled={attente}
                            aria-label="Ajouter « {s.texte} »">Ajouter</Button>
                  {/if}
                </li>
              {/each}
            </ul>
            {#if d.sillage?.message}<p class="mt-2 text-xs text-muted-foreground">Sillage : {d.sillage.message}</p>{/if}
          </section>
        {/if}

        <!-- toutes les rubriques, repliables -->
        {#each d.rubriques.familles as f}
          <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label={f.titre}>
            <h2 class="etiquette mb-2">{f.titre}</h2>
            <div class="grid gap-1.5">
              {#each f.rubriques as r}
                {@const miennes = de(r.cle)}
                <details class="min-w-0 rounded-xl border px-3 py-2 open:bg-background/40">
                  <summary class="flex cursor-pointer items-center justify-between gap-2 text-sm">
                    <span class="min-w-0 break-words font-medium">{r.titre}</span>
                    <span class="shrink-0 rounded-full border px-2 text-xs {miennes.length ? 'border-valide/60 text-valide' : 'text-muted-foreground'}">{miennes.length}</span>
                  </summary>
                  <div class="mt-2 grid min-w-0 gap-2">
                    {#if miennes.length}<ul class="grid gap-1.5">{#each miennes as p (p.id)}{@render pepite(p)}{/each}</ul>{/if}
                    {@render saisie(r.cle, r.suggestions, r.titre)}
                  </div>
                </details>
              {/each}
            </div>
          </section>
        {/each}
      </div>

      <aside class="grid min-w-0 content-start gap-4 lg:sticky lg:top-4">
        <section class="rounded-2xl border bg-card p-4" aria-label="Jauge">
          <h2 class="etiquette mb-1">Jauge</h2>
          <p class="text-2xl font-light"><span>{jauge.nombre}</span> pépite{jauge.nombre > 1 ? 's' : ''}</p>
          <p class="text-sm text-muted-foreground">{jauge.palier ? `« ${jauge.palier} »` : 'pas encore de quoi rire'}{jauge.prochain ? ` · prochain palier à ${jauge.prochain}` : ''}</p>
          <div class="mt-2 h-2 overflow-hidden rounded-full bg-secondary" role="progressbar" aria-valuemin="0" aria-valuemax="30" aria-valuenow={jauge.nombre} aria-label="Pépites">
            <div class="h-full rounded-full bg-primary transition-all" style="width: {largeurJauge}%"></div>
          </div>
          <p class="mt-1 flex justify-between text-[0.7rem] text-muted-foreground">{#each d.paliers as pl}<span>{pl.seuil} · {pl.nom}</span>{/each}</p>
        </section>

        <!-- sujets interdits : à part, masqués par défaut -->
        <section class="rounded-2xl border border-destructive/40 bg-card p-4" aria-label="Sujets interdits">
          <div class="flex items-center justify-between gap-2">
            <h2 class="etiquette">Sujets interdits ({interdits.length})</h2>
            <Button size="xs" variant="ghost" onclick={() => (voirInterdits = !voirInterdits)} aria-expanded={voirInterdits}>
              {#if voirInterdits}<EyeOff class="size-3" aria-hidden="true" />Masquer{:else}<Eye class="size-3" aria-hidden="true" />Afficher{/if}</Button>
          </div>
          <p class="mt-1 text-xs text-muted-foreground">Jamais envoyés à l'IA ; toute proposition qui en parle est écartée, pour chaque personne du numéro.</p>
          {#if voirInterdits}
            <div class="mt-2 grid min-w-0 gap-2">
              {#if interdits.length}<ul class="grid gap-1.5">{#each interdits as p (p.id)}{@render pepite(p)}{/each}</ul>{/if}
              {@render saisie('interdits', d.rubriques.interdits.suggestions, 'Sujets interdits')}
            </div>
          {/if}
        </section>
      </aside>
    </div>
  {/if}
{:else}
  <p class="text-sm text-muted-foreground">Lecture de la fiche…</p>
{/if}
