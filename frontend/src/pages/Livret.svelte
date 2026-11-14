<script>
  // Un livret : relecture bloc par bloc à gauche, aperçu des 4 pages à droite. « Approuver » contrôle
  // d'abord qu'aucune page ne déborde. Rien ne s'imprime sans approbation.
  import { onMount, onDestroy } from 'svelte'
  import ArrowLeft from '@lucide/svelte/icons/arrow-left'
  import Cake from '@lucide/svelte/icons/cake'
  import Download from '@lucide/svelte/icons/download'
  import EyeOff from '@lucide/svelte/icons/eye-off'
  import Eye from '@lucide/svelte/icons/eye'
  import Replace from '@lucide/svelte/icons/replace'
  import Plus from '@lucide/svelte/icons/plus'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Etat from '$lib/Etat.svelte'
  import FicheForm from '$lib/FicheForm.svelte'
  import Propositions from '$lib/Propositions.svelte'
  import { dateCourte, dateLongue, PORTEES } from '$lib/format.js'

  let { id, onchange, ondeconnecte } = $props()
  let d = $state(null)
  let contenu = $state(null)
  let mot = $state('')
  let modifie = $state(false)
  let message = $state('')
  let attente = $state('')
  let ouvert = $state(null)        // {bloc, index} du sélecteur de propositions
  let ficheOuverte = $state(false)
  let tampon = $state(Date.now())
  let largeur = $state(400)
  let minuteur = null

  async function lire() {
    try {
      d = await api.get(`/api/livrets/${id}`)
      contenu = JSON.parse(JSON.stringify(d.livret.contenu))
      mot = d.livret.mot || d.livret.mot_defaut
      modifie = false
      tampon = Date.now()
      clearTimeout(minuteur)
      if (d.livret.etat === 'en_preparation') minuteur = setTimeout(lire, 3000)
    } catch (err) {
      if (err.statut === 401) ondeconnecte?.()
      else message = err.message
    }
  }
  function toucher() { modifie = true; message = '' }

  async function enregistrer() {
    attente = 'enregistrer'
    try {
      await api.put(`/api/livrets/${id}`, { contenu: $state.snapshot(contenu), mot })
      await lire()
      message = 'Enregistré.'
      onchange?.()
    } catch (err) { message = err.message }
    attente = ''
  }
  async function choisir(bloc, f, index) {
    if (modifie) await api.put(`/api/livrets/${id}`, { contenu: $state.snapshot(contenu), mot })
    await api.post(`/api/livrets/${id}/choisir`, { bloc, proposition: f.id, index })
    ouvert = null
    await lire()
  }
  async function approuver() {
    if (modifie) await enregistrer()
    attente = 'approuver'
    try { await api.post(`/api/livrets/${id}/approuver`); await lire(); message = 'Livret approuvé.'; onchange?.() }
    catch (err) { message = err.message }
    attente = ''
  }
  async function preparer(relire = false) {
    if (relire && !confirm('Relire les sources oublie les pages gardées pour cette date et refait le livret (le mot des hôtes est gardé). Continuer ?')) return
    if (!relire && !confirm('Refaire le livret depuis les sources ? Les choix de blocs sont remplacés ; le mot des hôtes, la musique et le cinéma sont gardés.')) return
    await api.post(`/api/livrets/${id}/preparer`, { relire })
    await lire()
  }
  async function ajouterPhrase(a, phrase) {
    if (modifie) await enregistrer()
    await api.post(`/api/livrets/${id}/mot/ajouter`, { phrase, cle: a.cle })
    await lire()
    onchange?.()
  }
  async function remplirCulture() {
    if (modifie) await enregistrer()
    try { await api.post(`/api/livrets/${id}/culture`); await lire(); message = 'Musique et cinéma remplis depuis le top 5.' }
    catch (err) { message = err.message }
  }
  async function modifierFiche(fiche) {
    await api.put(`/api/personnes/${id}`, fiche)
    ficheOuverte = false
    await lire()
  }
  async function supprimer() {
    if (!confirm(`Supprimer la fiche et le livret de ${d.personne.nom} ?`)) return
    await api.del(`/api/personnes/${id}`)
    location.hash = '#/livrets'
  }
  function basculer(o) { o.masque = !o.masque; toucher() }
  function ouvrir(bloc, index = null) { ouvert = ouvert?.bloc === bloc && ouvert?.index === index ? null : { bloc, index } }
  const evts = $derived(d?.livret.propositions.evenements ?? [])
  const annee = $derived(d?.livret.propositions.annee ?? [])
  const pris = $derived(contenu ? [contenu.une?.id, ...(contenu.breves ?? []).map((b) => b.id), ...(contenu.p2?.items ?? []).map((b) => b.id),
                                   ...(contenu.chrono ?? []).map((b) => b.id)].filter(Boolean) : [])
  const echelle = $derived(Math.min(1, largeur / 600))

  onMount(lire)
  onDestroy(() => clearTimeout(minuteur))
</script>

{#snippet bouton(bloc, index, libelle = 'Remplacer')}
  <button type="button" class="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          onclick={() => ouvrir(bloc, index)} aria-expanded={ouvert?.bloc === bloc && ouvert?.index === index}>
    <Replace class="size-3.5" aria-hidden="true" />{libelle}
  </button>
{/snippet}
{#snippet masquer(o)}
  <button type="button" class="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground" onclick={() => basculer(o)}>
    {#if o.masque}<Eye class="size-3.5" aria-hidden="true" />Montrer{:else}<EyeOff class="size-3.5" aria-hidden="true" />Masquer{/if}
  </button>
{/snippet}

<a href="#/livrets" class="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
  <ArrowLeft class="size-4" aria-hidden="true" /> Livrets
</a>

{#if d && contenu}
  <header class="mb-5 flex flex-wrap items-end justify-between gap-3">
    <div>
      <p class="etiquette">né·e le {dateLongue(d.personne.naissance)}</p>
      <h1 class="titre">{d.personne.nom}</h1>
      <p class="mt-2 flex flex-wrap items-center gap-2">
        <Etat etat={d.livret.etat} />
        {#each d.sejours as s}<span class="text-xs text-muted-foreground">chambre {s.chambre}, {dateCourte(s.du)} → {dateCourte(s.jusqu_au)}</span>{/each}
      </p>
    </div>
    <div class="flex flex-wrap gap-2">
      {#if modifie}<Button variant="outline" onclick={enregistrer} disabled={!!attente}>Enregistrer</Button>{/if}
      <Button onclick={approuver} disabled={!!attente || d.livret.etat === 'en_preparation' || d.livret.etat === 'approuve' && !modifie}>
        {attente === 'approuver' ? 'Contrôle…' : d.livret.etat === 'approuve' && !modifie ? 'Approuvé' : 'Approuver'}
      </Button>
    </div>
  </header>

  {#if message}<p class="mb-4 rounded-xl border px-4 py-2 text-sm" role="status">{message}</p>{/if}
  {#if d.livret.erreur}<p class="mb-4 rounded-xl border border-destructive/60 px-4 py-2 text-sm text-destructive" role="alert">{d.livret.erreur}</p>{/if}

  {#each d.anniversaires.filter((a) => !a.ignore) as a}
    <section class="mb-4 rounded-2xl border border-primary/60 bg-card p-4" aria-label="Anniversaire">
      <p class="flex items-center gap-2 font-medium"><Cake class="size-5 text-primary" aria-hidden="true" />
        Anniversaire {a.libelle} : le {dateLongue(a.anniversaire)} (séjour du {dateCourte(a.sejour.du)} au {dateCourte(a.sejour.jusqu_au)})</p>
      <ul class="mt-2 grid gap-2">
        {#each a.phrases as p}
          <li class="flex flex-wrap items-center justify-between gap-2 text-sm">
            <span class="font-serif italic">« {p} »</span>
            <Button size="sm" variant="outline" onclick={() => ajouterPhrase(a, p)}>Ajouter au mot des hôtes</Button>
          </li>
        {/each}
      </ul>
    </section>
  {/each}

  {#if d.livret.etat === 'en_preparation'}
    <p class="mb-4 text-sm text-muted-foreground" role="status">Lecture des sources… (Wikipédia demande des pauses entre deux pages : une à deux minutes.)</p>
  {/if}

  <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
    <div class="grid min-w-0 content-start gap-4">
      <!-- La une -->
      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="La une">
        <div class="mb-2 flex items-center justify-between"><h2 class="etiquette">Page 1 · la une ({PORTEES[contenu.une?.portee] ?? '—'})</h2>{@render bouton('une', null, 'Changer')}</div>
        <input class="mb-2 w-full rounded-lg border bg-background px-3 py-2 font-serif text-lg font-semibold" bind:value={contenu.une.titre} oninput={toucher} aria-label="Gros titre" />
        <textarea class="w-full rounded-lg border bg-background px-3 py-2 text-sm" rows="3" bind:value={contenu.une.chapo} oninput={toucher} aria-label="Chapeau"></textarea>
        <div class="mt-2 grid grid-cols-3 gap-2 text-sm">
          <input class="min-w-0 rounded-lg border bg-background px-2 py-1" bind:value={contenu.une.encart.k} oninput={toucher} aria-label="Encart : rubrique" />
          <input class="min-w-0 rounded-lg border bg-background px-2 py-1 font-semibold" bind:value={contenu.une.encart.v} oninput={toucher} aria-label="Encart : nombre" />
          <input class="min-w-0 rounded-lg border bg-background px-2 py-1" bind:value={contenu.une.encart.l} oninput={toucher} aria-label="Encart : légende" />
        </div>
        {#if ouvert?.bloc === 'une'}<Propositions liste={evts} choisis={pris} onchoisir={(f) => choisir('une', f)} onfermer={() => (ouvert = null)} />{/if}
      </section>

      <!-- Brèves -->
      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Brèves">
        <div class="mb-2 flex items-center justify-between"><h2 class="etiquette">Page 1 · brèves</h2>{@render bouton('breve', null, 'Ajouter')}</div>
        {#if ouvert?.bloc === 'breve' && ouvert.index === null}<Propositions liste={evts} choisis={pris} onchoisir={(f) => choisir('breve', f, null)} onfermer={() => (ouvert = null)} />{/if}
        <ul class="grid gap-3">
          {#each contenu.breves as b, i}
            <li class="grid gap-1 {b.masque ? 'opacity-45' : ''}">
              <div class="flex flex-wrap items-center gap-2 sm:flex-nowrap">
                <input class="order-last min-w-0 flex-1 basis-full sm:order-none sm:basis-0 rounded-lg border bg-background px-2 py-1 text-sm font-semibold" bind:value={b.titre} oninput={toucher} aria-label="Titre de la brève {i + 1}" />
                {@render bouton('breve', i)}{@render masquer(b)}
              </div>
              <textarea class="rounded-lg border bg-background px-2 py-1 text-sm" rows="2" bind:value={b.texte} oninput={toucher} aria-label="Texte de la brève {i + 1}"></textarea>
              {#if ouvert?.bloc === 'breve' && ouvert.index === i}<Propositions liste={evts} choisis={pris} onchoisir={(f) => choisir('breve', f, i)} onfermer={() => (ouvert = null)} />{/if}
            </li>
          {/each}
        </ul>
      </section>

      <!-- Page 2 -->
      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Page 2">
        <div class="mb-2 flex items-center justify-between"><h2 class="etiquette">Page 2 · {contenu.p2.mode === 'mois' ? 'les titres du mois' : 'la semaine'}</h2>{@render bouton('p2', null, 'Ajouter')}</div>
        {#if ouvert?.bloc === 'p2' && ouvert.index === null}<Propositions liste={evts} choisis={pris} onchoisir={(f) => choisir('p2', f, null)} onfermer={() => (ouvert = null)} />{/if}
        <ul class="grid gap-3">
          {#each contenu.p2.items as it, i}
            <li class="grid gap-1 {it.masque ? 'opacity-45' : ''}">
              <div class="flex flex-wrap items-center gap-2 sm:flex-nowrap">
                <span class="w-14 shrink-0 text-xs text-muted-foreground">{dateCourte(it.date)}</span>
                <input class="order-last min-w-0 flex-1 basis-full sm:order-none sm:basis-0 rounded-lg border bg-background px-2 py-1 text-sm font-semibold" bind:value={it.titre} oninput={toucher} aria-label="Titre {i + 1}" />
                {@render bouton('p2', i)}{@render masquer(it)}
              </div>
              <textarea class="rounded-lg border bg-background px-2 py-1 text-sm" rows="2" bind:value={it.texte} oninput={toucher} aria-label="Texte {i + 1}"></textarea>
              {#if ouvert?.bloc === 'p2' && ouvert.index === i}<Propositions liste={evts} choisis={pris} onchoisir={(f) => choisir('p2', f, i)} onfermer={() => (ouvert = null)} />{/if}
            </li>
          {/each}
        </ul>
      </section>

      <!-- Page 3 -->
      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Chronologie">
        <div class="mb-2 flex items-center justify-between"><h2 class="etiquette">Page 3 · chronologie de l'année</h2>{@render bouton('chrono', null, 'Ajouter')}</div>
        {#if ouvert?.bloc === 'chrono' && ouvert.index === null}<Propositions liste={annee} choisis={pris} onchoisir={(f) => choisir('chrono', f, null)} onfermer={() => (ouvert = null)} />{/if}
        <ul class="grid gap-2">
          {#each contenu.chrono as c, i}
            <li class="{c.masque ? 'opacity-45' : ''}">
              <div class="flex flex-wrap items-center gap-2 sm:flex-nowrap">
                <input class="w-20 shrink-0 rounded-lg border bg-background px-2 py-1 text-xs" bind:value={c.quand} oninput={toucher} aria-label="Date du repère {i + 1}" />
                <input class="order-last min-w-0 flex-1 basis-full sm:order-none sm:basis-0 rounded-lg border bg-background px-2 py-1 text-sm" bind:value={c.texte} oninput={toucher} aria-label="Repère {i + 1}" />
                {@render bouton('chrono', i)}{@render masquer(c)}
              </div>
              {#if ouvert?.bloc === 'chrono' && ouvert.index === i}<Propositions liste={annee} choisis={pris} onchoisir={(f) => choisir('chrono', f, i)} onfermer={() => (ouvert = null)} />{/if}
            </li>
          {/each}
        </ul>
        <div class="mt-4 flex flex-wrap items-center justify-between gap-2">
          <span class="etiquette">Culture de l'année</span>
          <Button variant="outline" size="sm" onclick={remplirCulture}>Remplir depuis le top 5</Button>
        </div>
        {#if d.livret.propositions.culture}
          {@const top = d.livret.propositions.culture}
          <details class="mt-1 text-xs text-muted-foreground"><summary class="cursor-pointer">Top 5 de l'année</summary>
            <div class="mt-2 grid gap-2 sm:grid-cols-3">
              {#each [['Film', 'Films'], ['Serie', 'Séries'], ['Musique', 'Musique']] as [cat, nom]}
                <div>
                  <p class="font-medium text-foreground">{nom}</p>
                  <ol class="mt-1 grid gap-0.5">
                    {#each top[cat] ?? [] as x}
                      <li>{x.rang}. {x.titre}{x.createur ? ' — ' + x.createur : ''}
                        {#if x.provisoire}<span class="text-primary"> (provisoire)</span>{/if}
                        {#if x.metrique.includes('à vérifier')}<span class="text-destructive"> (à vérifier)</span>{/if}</li>
                    {:else}<li>—</li>{/each}
                  </ol>
                </div>
              {/each}
            </div>
          </details>
        {/if}
        <div class="mt-3 grid gap-3 sm:grid-cols-2">
          <label class="grid gap-1 text-sm"><span class="etiquette">Musique</span>
            <textarea rows="3" class="min-w-0 rounded-lg border bg-background px-2 py-1" bind:value={contenu.musique} oninput={toucher} placeholder="n°1 des ventes de la semaine (vide : rubrique absente)"></textarea></label>
          <label class="grid gap-1 text-sm"><span class="etiquette">Cinéma</span>
            <textarea rows="3" class="min-w-0 rounded-lg border bg-background px-2 py-1" bind:value={contenu.cinema} oninput={toucher} placeholder="films à l'affiche (vide : rubrique absente)"></textarea></label>
        </div>
        <div class="mt-4 grid gap-3 sm:grid-cols-2">
          {#each [['nes', 'Nés le même jour'], ['morts', 'Disparus le même jour']] as [cle, libelle]}
            <div>
              <p class="etiquette mb-1">{libelle}</p>
              <ul class="grid gap-1 text-sm">
                {#each contenu[cle] as p}
                  <li class="flex items-center justify-between gap-2 {p.masque ? 'opacity-45' : ''}"><span>{p.nom} ({p.annee})</span>{@render masquer(p)}</li>
                {/each}
              </ul>
              {#if (d.livret.propositions[cle] ?? []).length > contenu[cle].length}
                <details class="mt-1 text-xs text-muted-foreground"><summary class="cursor-pointer">Ajouter</summary>
                  <ul class="mt-1 grid gap-0.5">
                    {#each d.livret.propositions[cle].filter((p) => !contenu[cle].some((x) => x.nom === p.nom)) as p}
                      <li><button type="button" class="hover:text-foreground" onclick={() => { contenu[cle] = [...contenu[cle], { nom: p.nom, annee: p.annee }]; toucher() }}>
                        <Plus class="inline size-3" aria-hidden="true" /> {p.nom} ({p.annee})</button></li>
                    {/each}
                  </ul>
                </details>
              {/if}
            </div>
          {/each}
        </div>
      </section>

      <!-- Page 4 -->
      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Le mot des hôtes">
        <h2 class="etiquette mb-2">Page 4 · le mot des hôtes</h2>
        <textarea class="w-full rounded-lg border bg-background px-3 py-2 font-serif" rows="8" bind:value={mot} oninput={toucher} aria-label="Mot des hôtes"></textarea>
        <p class="mt-1 text-xs text-muted-foreground">Une ligne vide sépare les paragraphes. Signature : « {d.signature} » (Réglages › Le journal).</p>
      </section>

      <!-- Fiche et gestes -->
      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Fiche">
        <div class="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onclick={() => (ficheOuverte = !ficheOuverte)}>Modifier la fiche</Button>
          <Button variant="outline" size="sm" onclick={() => preparer(false)} disabled={d.livret.etat === 'en_preparation'}>Préparer de nouveau</Button>
          <Button variant="outline" size="sm" onclick={() => preparer(true)} disabled={d.livret.etat === 'en_preparation'}>Relire les sources</Button>
          <Button variant="ghost" size="sm" class="text-destructive" onclick={supprimer}>Supprimer</Button>
        </div>
        {#if ficheOuverte}<div class="mt-4"><FicheForm valeur={d.personne} bouton="Enregistrer la fiche" onvalider={modifierFiche} onannuler={() => (ficheOuverte = false)} /></div>{/if}
        {#if contenu.notes?.length}<p class="mt-3 text-xs text-muted-foreground">Sources en défaut : {contenu.notes.join(' ; ')}</p>{/if}
      </section>
    </div>

    <!-- Aperçu -->
    <aside class="lg:sticky lg:top-6 lg:self-start" aria-label="Aperçu">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 class="etiquette">Aperçu{modifie ? ' (enregistre pour mettre à jour)' : ''}</h2>
        <span class="flex gap-3 text-xs">
          <a class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" href={`/api/livrets/${id}/pdf?mode=impose`}><Download class="size-3.5" aria-hidden="true" />PDF à imprimer</a>
          <a class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" href={`/api/livrets/${id}/pdf?mode=lecture`}><Download class="size-3.5" aria-hidden="true" />PDF lecture</a>
        </span>
      </div>
      <div class="max-h-[78vh] overflow-y-auto rounded-xl border" bind:clientWidth={largeur}>
        <div style="height:{Math.round(3480 * echelle)}px;position:relative;overflow:hidden">
          <iframe title="Aperçu du livret" src={`/api/livrets/${id}/apercu?mode=ecran&t=${tampon}`} scrolling="no"
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
