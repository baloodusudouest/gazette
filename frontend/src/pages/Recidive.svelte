<script>
  // 0.9 : une édition de La Récidive (journal à scandale, à partir du 2e séjour) — relecture à gauche (N°, accroche,
  // photos et légendes, retrait, mot des hôtes), aperçu des 4 pages à droite. « Approuver » contrôle d'abord
  // qu'aucune page ne déborde. Rien ne s'imprime sans approbation. Légendes de gabarit ; 0.9.1 : Julien décrit une
  // photo en quelques mots, l'IA du PC propose 5 titres (60 caractères au plus), il en choisit un ou écrit le sien.
  import { onMount, onDestroy } from 'svelte'
  import ArrowLeft from '@lucide/svelte/icons/arrow-left'
  import Download from '@lucide/svelte/icons/download'
  import EyeOff from '@lucide/svelte/icons/eye-off'
  import Eye from '@lucide/svelte/icons/eye'
  import RefreshCw from '@lucide/svelte/icons/refresh-cw'
  import Sparkles from '@lucide/svelte/icons/sparkles'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Etat from '$lib/Etat.svelte'
  import { dateCourte, dateLongue } from '$lib/format.js'

  let { id, onchange, ondeconnecte } = $props()
  let d = $state(null)
  let photos = $state([])
  let mot = $state('')
  let accroche = $state('')
  let numero = $state('')
  let titreUne = $state('')
  let macaron = $state('hd')         // 0.9.2 : place du macaron « Exclusif ! »
  let descriptionUne = $state('')
  let propsUne = $state([])
  let demande = $state('')          // cible en cours de proposition (« une » ou id de photo)
  let lot = $state(null)            // « IA » sur tout : {fait, total}
  let rumeurs = $state([])          // 0.9.7 : rumeurs imprimées en page 3
  let indices = $state('')
  let propsRumeurs = $state([])
  let modifie = $state(false)
  let message = $state('')
  let attente = $state('')
  let tampon = $state(Date.now())
  let largeur = $state(400)
  let minuteur = null

  async function lire() {
    try {
      d = await api.get(`/api/recidives/${id}`)
      const ed = d.edition
      photos = ed.photos.map((p) => ({ ...p }))
      mot = ed.mot || ed.mot_defaut
      accroche = ed.accroche || ed.accroche_defaut
      numero = ed.numero_main ?? ''
      titreUne = ed.titre_une || ''
      macaron = ed.macaron || 'hd'
      descriptionUne = ed.description_une || ''
      propsUne = ed.propositions_une || []
      rumeurs = (ed.rumeurs || []).map((r) => r.replace(/^\s*(\d+\s*[.)\-:–—/]+|[-•*–—])\s*/, ''))   // 0.9.8 : numéros de l'IA
      indices = ed.indices_rumeurs || d.indices_carnet || ''      // 0.10 : repris de carnet (« Pour les journaux »)
      propsRumeurs = ed.propositions_rumeurs || []
      modifie = false
      tampon = Date.now()
      clearTimeout(minuteur)
      if (ed.etat === 'en_preparation') minuteur = setTimeout(lire, 3000)
    } catch (err) {
      if (err.statut === 401) ondeconnecte?.()
      else message = err.message
    }
  }
  function toucher() { modifie = true; message = '' }
  const corps = () => ({ numero_main: numero === '' ? null : +numero, accroche, mot, titre_une: titreUne, description_une: descriptionUne, macaron, rumeurs, indices_rumeurs: indices,
                         photos: photos.map((p) => ({ id: p.id, legende: p.legende, retiree: p.retiree, description: p.description ?? '', cadrage: p.cadrage ?? 'haut' })) })
  // « IA » en haut : 5 titres pour chaque texte décrit (la une et chaque photo gardée), l'un après l'autre
  const cibles = () => [...(descriptionUne.trim().length >= 3 ? ['une'] : []),
                        ...photos.filter((p) => !p.retiree && (p.description ?? '').trim().length >= 3).map((p) => p.id)]
  async function proposerRumeurs() {
    demande = 'rumeurs'
    message = ''
    try {
      const r = await api.post(`/api/recidives/${id}/rumeurs`, { indices })
      propsRumeurs = r.propositions
      if (indices.trim() && r.carnet) message = `Indices : ${r.carnet}.`
      toucher()
    }
    catch (err) { message = err.message }
    demande = ''
  }
  function prendreRumeur(t) {
    if (rumeurs.includes(t)) return
    if (rumeurs.length >= d.rumeurs_maxi) { message = `${d.rumeurs_maxi} rumeurs au plus : retires-en une d'abord.`; return }
    rumeurs = [...rumeurs, t]; toucher()
  }
  async function proposerTout() {
    const liste = cibles()
    if (!liste.length) { message = 'Décris d\'abord au moins une photo (case « Décris… » sous la une ou sous une photo).'; return }
    lot = { fait: 0, total: liste.length }
    let echecs = 0
    for (const c of liste) {
      await proposer(c)
      if (message) { echecs++; if (message.includes('injoignable') || message.includes('pas réglée')) break }
      lot = { fait: lot.fait + 1, total: lot.total }
    }
    if (!echecs && !rumeurs.length) { await proposerRumeurs(); if (message) echecs++ }
    if (!echecs) message = `Propositions prêtes pour ${liste.length} texte${liste.length > 1 ? 's' : ''} : touche celles qui te plaisent, puis Enregistrer.`
    lot = null
  }
  async function proposer(cible) {
    const description = cible === 'une' ? descriptionUne : photos.find((p) => p.id === cible)?.description ?? ''
    demande = cible
    message = ''
    try {
      const r = await api.post(`/api/recidives/${id}/proposer`, { cible, description })
      if (cible === 'une') propsUne = r.propositions
      else { const p = photos.find((x) => x.id === cible); p.propositions = r.propositions }
      toucher()
    } catch (err) { message = err.message }
    demande = ''
  }
  async function enregistrer() {
    attente = 'enregistrer'
    try { await api.put(`/api/recidives/${id}`, corps()); await lire(); message = 'Enregistré.'; onchange?.() }
    catch (err) { message = err.message }
    attente = ''
  }
  async function approuver() {
    if (modifie) await enregistrer()
    attente = 'approuver'
    try { await api.post(`/api/recidives/${id}/approuver`); await lire(); message = 'Édition approuvée : prête à imprimer.'; onchange?.() }
    catch (err) { message = err.message }
    attente = ''
  }
  async function preparer(completer) {
    if (!completer && !confirm('Refaire le choix des photos depuis Immich ? Les légendes écrites sont perdues ; le mot, l\'accroche et le N° corrigé sont gardés.')) return
    if (modifie) await api.put(`/api/recidives/${id}`, corps())
    await api.post(`/api/recidives/${id}/preparer`, { completer })
    await lire()
  }
  function basculer(p) { p.retiree = !p.retiree; toucher() }
  const vues = $derived(photos.filter((p) => !p.retiree))
  const echelle = $derived(Math.min(1, largeur / 600))
  const ed = $derived(d?.edition)
  onMount(lire)
  onDestroy(() => clearTimeout(minuteur))
</script>

{#snippet ia(cible, description, props, ecrire, choisir)}
  <div class="mt-2 grid min-w-0 gap-1.5 rounded-lg border border-dashed p-2">
    <span class="text-[0.7rem] font-medium tracking-wide text-muted-foreground uppercase">Pour l'IA (non imprimé)</span>
    <div class="flex min-w-0 flex-wrap items-center justify-end gap-2">
      <input class="w-full min-w-0 rounded-lg border bg-background px-2 py-1 text-sm" maxlength="400" value={description}
             oninput={(e) => ecrire(e.currentTarget.value)} placeholder={cible === 'une' ? "Décris la photo de la une (l'IA proposera 5 gros titres)" : "Décris cette photo (l'IA proposera 5 légendes)"}
             aria-label={cible === 'une' ? 'Description de la photo de la une' : 'Description de la photo'} />
      <Button size="sm" variant="outline" class="shrink-0" onclick={() => proposer(cible)} disabled={demande !== '' || description.trim().length < 3}>
        <Sparkles class="size-3.5" aria-hidden="true" />{demande === cible ? '…' : '5 titres'}</Button>
    </div>
    {#if props.length}
      <ul class="grid gap-1" aria-label="Propositions de l'IA">
        {#each props as t}
          <li><button type="button" class="w-full rounded-md px-2 py-1 text-left text-sm break-words whitespace-normal hover:bg-secondary" onclick={() => choisir(t)}>« {t} » <span class="text-xs text-muted-foreground">{t.length}</span></button></li>
        {/each}
      </ul>
    {/if}
  </div>
{/snippet}

{#if d}
  <header class="sticky top-0 z-10 -mx-2 mb-5 flex flex-wrap items-end justify-between gap-3 bg-background/90 px-2 py-2 backdrop-blur">
    <div>
      <a href="#/livrets" class="mb-1 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft class="size-4" aria-hidden="true" />Livrets</a>
      <p class="etiquette">La Récidive · N° {ed.numero_main ?? ed.numero}</p>
      <h1 class="titre flex flex-wrap items-center gap-3">{d.personne.nom} <Etat etat={ed.etat} /></h1>
      <p class="mt-1 text-sm text-muted-foreground">Séjour du {dateLongue(ed.sejour_du)}
        {#if ed.precedent} · photos depuis le {dateLongue(ed.precedent.du)}{/if}
        · {ed.trouvees} photo{ed.trouvees > 1 ? 's' : ''} trouvée{ed.trouvees > 1 ? 's' : ''} dans Immich</p>
    </div>
    <div class="flex flex-wrap gap-2">
      <Button variant="outline" onclick={proposerTout} disabled={lot !== null || demande !== '' || !['a_relire', 'approuve'].includes(ed.etat)}
              title="5 titres proposés par l'IA du PC pour chaque photo décrite">
        <Sparkles class="size-4" aria-hidden="true" />{lot ? `IA ${lot.fait}/${lot.total}…` : 'IA'}</Button>
      <Button variant="outline" onclick={enregistrer} disabled={!modifie || attente !== ''}>{attente === 'enregistrer' ? 'Enregistrement…' : 'Enregistrer'}</Button>
      <Button onclick={approuver} disabled={attente !== '' || !['a_relire', 'approuve'].includes(ed.etat) || ed.etat === 'approuve' && !modifie}>
        {attente === 'approuver' ? 'Contrôle…' : ed.etat === 'approuve' && !modifie ? 'Approuvée' : 'Approuver'}</Button>
    </div>
  </header>

  {#if message}<p class="mb-4 rounded-xl border px-4 py-2 text-sm" role="status">{message}</p>{/if}
  {#if ed.erreur}<p class="mb-4 rounded-xl border border-destructive/60 px-4 py-2 text-sm text-destructive" role="alert">{ed.erreur}</p>{/if}
  {#if ed.etat === 'vide'}
    <p class="mb-4 rounded-xl border px-4 py-2 text-sm">Aucune photo de {d.personne.prenom || d.personne.nom} depuis le séjour précédent : ce séjour garde la <a class="underline" href={'#/livret/' + d.personne.id}>Gazette</a>.</p>
  {/if}
  {#if ed.manque_scandale && ed.etat === 'a_relire'}
    <p class="mb-4 rounded-xl border border-primary/50 px-4 py-2 text-sm">{vues.length} photo{vues.length > 1 ? 's' : ''} sur {d.places} :
      {ed.tag_absent ? 'le tag « scandale » n\'existe pas encore dans Immich.' : 'aucune photo de la personne avec le tag « scandale » dans Immich.'}
      Tague quelques vieilles photos, puis « Compléter ».</p>
  {/if}

  <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
    <div class="grid min-w-0 content-start gap-4">
      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Une">
        <h2 class="etiquette mb-2">Page 1 · la une</h2>
        <div class="grid gap-3 sm:grid-cols-[8rem_minmax(0,1fr)]">
          <label class="grid gap-1 text-sm"><span class="etiquette">N° (corrigé)</span>
            <input type="number" min="2" max="99" placeholder={String(ed.numero)} class="rounded-lg border bg-background px-2 py-1" bind:value={numero} oninput={toucher} /></label>
          <label class="grid gap-1 text-sm"><span class="etiquette">Accroche sous le titre</span>
            <input class="rounded-lg border bg-background px-2 py-1" maxlength="80" bind:value={accroche} oninput={toucher} /></label>
        </div>
        <p class="mt-1 text-xs text-muted-foreground">N° vide : celui du séjour ({ed.numero}). Accroche proposée d'après le genre de la fiche carnet : « {ed.accroche_defaut} ».</p>
        <label class="mt-3 grid gap-1 text-sm"><span class="etiquette">Gros titre de la une (imprimé)</span>
          <input class="rounded-lg border bg-background px-2 py-1" maxlength="90" placeholder={d.titre_defaut} bind:value={titreUne} oninput={toucher} /></label>
        <fieldset class="mt-3 grid gap-1 text-sm">
          <legend class="etiquette mb-1">Macaron « Exclusif ! » sur la photo</legend>
          <div class="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Place du macaron">
            {#each Object.entries(d.macarons) as [cle, nom]}
              <button type="button" role="radio" aria-checked={macaron === cle} onclick={() => { macaron = cle; toucher() }}
                      class="rounded-full border px-3 py-1 text-xs aria-checked:border-primary aria-checked:bg-primary aria-checked:text-primary-foreground">{nom}</button>
            {/each}
          </div>
        </fieldset>
        {@render ia('une', descriptionUne, propsUne, (v) => { descriptionUne = v; toucher() }, (t) => { titreUne = t; toucher() })}
      </section>

      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Photos">
        <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h2 class="etiquette">Les preuves · {vues.length} photo{vues.length > 1 ? 's' : ''} sur {d.places}</h2>
          <span class="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onclick={() => preparer(true)} disabled={ed.etat === 'en_preparation'}><RefreshCw class="size-3.5" aria-hidden="true" />Compléter</Button>
            <Button size="sm" variant="ghost" onclick={() => preparer(false)} disabled={ed.etat === 'en_preparation'}>Tout refaire</Button>
          </span>
        </div>
        <p class="mb-3 text-xs text-muted-foreground">La première photo fait la une. « Retirer » écarte une photo (elle ne reviendra pas) ; « Compléter » cherche de quoi remplir les places libres.</p>
        <ul class="grid gap-3 sm:grid-cols-2">
          {#each photos as p, i (p.id)}
            <li class="flex min-w-0 flex-col gap-2 rounded-xl border p-2 {p.retiree ? 'opacity-45' : ''}">
              <div class="relative aspect-[4/3] overflow-hidden rounded-lg bg-muted">
                <img src={`/api/recidives/${id}/photos/${p.id}`} alt="Photo du {dateLongue(p.date)}" loading="lazy"
                     class="size-full {p.cadrage === 'entiere' ? 'object-contain bg-black' : 'object-cover'} {p.ancien ? 'grayscale sepia-[.35]' : ''}"
                     style="object-position:50% {({ haut: '20%', centre: '50%', bas: '85%' })[p.cadrage ?? 'haut'] ?? '50%'}" />
                <span class="absolute bottom-1 left-1 rounded bg-black/75 px-1.5 text-[0.7rem] text-white">
                  {p.ancien ? 'Ancien scandale' : i === 0 ? 'En une' : 'Récente'} · {dateCourte(p.date)}</span>
              </div>
              {#if !p.retiree}
                <div class="flex flex-wrap items-center gap-1" role="radiogroup" aria-label="Cadrage de la photo du {dateLongue(p.date)}">
                  {#each Object.entries(d.cadrages) as [cle, nom]}
                    <button type="button" role="radio" aria-checked={(p.cadrage ?? 'haut') === cle} onclick={() => { p.cadrage = cle; toucher() }}
                            class="rounded-full border px-2 py-0.5 text-[0.7rem] aria-checked:border-primary aria-checked:bg-primary aria-checked:text-primary-foreground">{nom}</button>
                  {/each}
                </div>
              {/if}
              <span class="text-[0.7rem] font-medium tracking-wide text-muted-foreground uppercase">Légende imprimée</span>
              <textarea rows="2" class="min-w-0 rounded-lg border bg-background px-2 py-1 font-mono text-sm" maxlength="220" bind:value={p.legende}
                        oninput={toucher} aria-label="Légende de la photo du {dateLongue(p.date)}" disabled={p.retiree}></textarea>
              {#if !p.retiree}{@render ia(p.id, p.description ?? '', p.propositions ?? [], (v) => { p.description = v; toucher() }, (t) => { p.legende = t; toucher() })}{/if}
              <button type="button" class="inline-flex items-center gap-1 self-start text-xs text-muted-foreground hover:text-foreground" onclick={() => basculer(p)}>
                {#if p.retiree}<Eye class="size-3.5" aria-hidden="true" />Remettre{:else}<EyeOff class="size-3.5" aria-hidden="true" />Retirer{/if}
              </button>
            </li>
          {:else}
            <li class="text-sm text-muted-foreground">{ed.etat === 'en_preparation' ? 'Recherche des photos dans Immich…' : 'Aucune photo.'}</li>
          {/each}
        </ul>
      </section>

      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Rumeurs">
        <h2 class="etiquette mb-2">Page 3 · les rumeurs de la rédaction ({rumeurs.length}/{d.rumeurs_maxi})</h2>
        <p class="mb-2 text-xs text-muted-foreground">Des scandales loufoques, tout inventés, pour remplir la page 3. Imprimées avec la mention « tout est inventé ».</p>
        <span class="text-[0.7rem] font-medium tracking-wide text-muted-foreground uppercase">Rumeurs imprimées</span>
        <ul class="mt-1 grid gap-1.5">
          {#each rumeurs as r, i}
            <li class="flex min-w-0 items-start gap-2">
              <textarea rows="2" class="min-w-0 flex-1 rounded-lg border bg-background px-2 py-1 text-sm" maxlength="160" value={r}
                        oninput={(e) => { rumeurs[i] = e.currentTarget.value; toucher() }} aria-label="Rumeur {i + 1}"></textarea>
              <button type="button" class="text-xs text-muted-foreground hover:text-foreground" onclick={() => { rumeurs = rumeurs.filter((_, j) => j !== i); toucher() }}>Retirer</button>
            </li>
          {:else}<li class="text-sm text-muted-foreground">Aucune : la page 3 garde son espace libre.</li>{/each}
        </ul>
        {#if rumeurs.length < d.rumeurs_maxi}
          <button type="button" class="mt-1 text-xs text-muted-foreground hover:text-foreground" onclick={() => { rumeurs = [...rumeurs, '']; toucher() }}>+ Écrire une rumeur</button>
        {/if}
        <div class="mt-3 grid min-w-0 gap-1.5 rounded-lg border border-dashed p-2">
          <span class="text-[0.7rem] font-medium tracking-wide text-muted-foreground uppercase">Pour l'IA (non imprimé)</span>
          <div class="flex min-w-0 flex-wrap items-center justify-end gap-2">
            <input class="w-full min-w-0 rounded-lg border bg-background px-2 py-1 text-sm" maxlength="400" bind:value={indices} oninput={toucher}
                   placeholder="Ce qu'on sait d'elle ou de lui (facultatif) : passions, manies, petites histoires…" aria-label="Indices pour les rumeurs" />
            <Button size="sm" variant="outline" class="shrink-0" onclick={proposerRumeurs} disabled={demande !== '' || lot !== null}>
              <Sparkles class="size-3.5" aria-hidden="true" />{demande === 'rumeurs' ? '…' : '8 rumeurs'}</Button>
          </div>
          <p class="text-[0.7rem] text-muted-foreground">Gardé dans carnet (fiche › Pour les journaux), repris au prochain séjour.</p>
          {#if propsRumeurs.length}
            <ul class="grid gap-1" aria-label="Rumeurs proposées par l'IA">
              {#each propsRumeurs as t}
                <li><button type="button" class="w-full rounded-md px-2 py-1 text-left text-sm break-words whitespace-normal hover:bg-secondary disabled:opacity-40"
                            disabled={rumeurs.includes(t)} onclick={() => prendreRumeur(t)}>+ {t}</button></li>
              {/each}
            </ul>
          {/if}
        </div>
      </section>

      {#if d.deja_paru?.length}
        <details class="min-w-0 rounded-2xl border bg-card p-4 text-sm">
          <summary class="etiquette cursor-pointer">Déjà paru dans les numéros précédents ({d.deja_paru.length})</summary>
          <p class="mt-1 text-xs text-muted-foreground">L'IA ne les repropose pas, mais peut y faire un clin d'œil.</p>
          <ul class="mt-2 grid gap-1">{#each d.deja_paru as t}<li>« {t} »</li>{/each}</ul>
        </details>
      {/if}

      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Droit de réponse">
        <h2 class="etiquette mb-2">Page 4 · droit de réponse (le mot des hôtes)</h2>
        <textarea class="w-full rounded-lg border bg-background px-3 py-2 font-serif" rows="7" bind:value={mot} oninput={toucher} aria-label="Mot des hôtes"></textarea>
        <p class="mt-1 text-xs text-muted-foreground">Une ligne vide sépare les paragraphes. Signature : « {d.signature} » (Réglages › Le journal). Aucune date de naissance dans ce journal.</p>
      </section>
    </div>

    <aside class="lg:sticky lg:top-6 lg:self-start" aria-label="Aperçu">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 class="etiquette">Aperçu{modifie ? ' (enregistre pour mettre à jour)' : ''}</h2>
        <span class="flex gap-3 text-xs">
          <a class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" href={`/api/recidives/${id}/pdf?mode=impose`}><Download class="size-3.5" aria-hidden="true" />PDF à imprimer</a>
          <a class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" href={`/api/recidives/${id}/pdf?mode=lecture`}><Download class="size-3.5" aria-hidden="true" />PDF lecture</a>
        </span>
      </div>
      <div class="max-h-[78vh] overflow-y-auto rounded-xl border" bind:clientWidth={largeur}>
        <div style="height:{Math.round(3480 * echelle)}px;position:relative;overflow:hidden">
          <iframe title="Aperçu de La Récidive" src={`/api/recidives/${id}/apercu?mode=ecran&t=${tampon}`} scrolling="no"
                  style="position:absolute;top:0;left:0;width:600px;height:3480px;border:0;transform:scale({echelle});transform-origin:0 0"></iframe>
        </div>
      </div>
      <p class="mt-2 text-xs text-muted-foreground">Impression : A4 paysage, recto-verso bord court, puis plier en deux.</p>
    </aside>
  </div>
{:else if message}
  <p class="text-sm text-destructive" role="alert">{message}</p>
{:else}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}
