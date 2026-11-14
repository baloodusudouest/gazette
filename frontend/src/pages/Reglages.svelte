<script>
  // « Réglages » : ce qui vient de la stack (affiché), le journal, la version et la déconnexion.
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  let { session, deconnecter } = $props()
  let r = $state(null)
  let c = $state(null)
  let message = $state('')
  let copie = $state(false)
  let voirPrompt = $state(false)
  const GESTES = { preparation: 'livret préparé', approuver: 'livret approuvé', fiche: 'fiche', erreur: 'échec de préparation', culture: 'top 5 culturel', reglages: 'réglages' }

  let j = $state(null)
  let modifie = $state(false)
  let messageJ = $state('')
  let envoiJ = $state(false)
  async function lire() {
    try {
      r = await api.get('/api/reglages'); c = await api.get('/api/culture')
      j = { ...r.journal }; modifie = false
    } catch { /* déconnecté */ }
  }
  async function enregistrerJournal(e) {
    e.preventDefault()
    envoiJ = true; messageJ = ''
    try { await api.put('/api/reglages/journal', $state.snapshot(j)); await lire(); messageJ = 'Enregistré : vaut aussitôt pour tous les aperçus et les PDF.' }
    catch (err) { messageJ = err.message }
    envoiJ = false
  }
  async function importer(e) {
    const f = e.currentTarget.files?.[0]
    e.currentTarget.value = ''
    if (!f) return
    message = ''
    try {
      const etat = await api.post('/api/culture/import', { texte: await f.text() })
      message = `Fichier importé : ${etat.lignes} lignes, ${etat.annees[0]} à ${etat.annees[1]}. Les livrets déjà préparés gardent leur texte ; « Remplir depuis le top 5 » dans un livret le met à jour.`
      await lire()
    } catch (err) { message = err.message }
  }
  async function revenir() {
    if (!confirm('Revenir au fichier livré avec l\'appli ? Le fichier importé est retiré.')) return
    await api.post('/api/culture/revenir')
    message = 'Version livrée avec l\'appli rétablie.'
    await lire()
  }
  async function copier() {
    try { await navigator.clipboard.writeText(c.prompt); copie = true; setTimeout(() => (copie = false), 2000) }
    catch { voirPrompt = true }
  }
  onMount(lire)
</script>

<header class="mb-5">
  <p class="etiquette">Gazette</p>
  <h1 class="titre">Réglages</h1>
</header>

{#if r}
  {#if j}
    <form class="rounded-2xl border bg-card p-5" aria-label="Le journal" onsubmit={enregistrerJournal}>
      <h2 class="text-lg font-semibold">Le journal</h2>
      <p class="mt-1 text-sm text-muted-foreground">Ce qui est commun à tous les livrets. Un mot des hôtes déjà écrit dans un livret est gardé ; les autres prennent le mot par défaut.</p>
      <div class="mt-4 grid gap-3 sm:grid-cols-2">
        {#each ['titre', 'sous_titre', 'lieu', 'lieu_detail', 'chez', 'signature'] as cle}
          {@const ch = r.champs[cle]}
          <label class="grid gap-1 text-sm">
            <span class="text-muted-foreground">{ch.libelle}</span>
            <input class="h-10 rounded-lg border bg-background px-3" maxlength={ch.maxi} bind:value={j[cle]} oninput={() => (modifie = true)} />
            <span class="text-xs text-muted-foreground">{ch.aide}</span>
          </label>
        {/each}
        <label class="grid gap-1 text-sm sm:col-span-2">
          <span class="text-muted-foreground">{r.champs.mot_modele.libelle}</span>
          <textarea rows="6" class="rounded-lg border bg-background px-3 py-2 font-serif" maxlength={r.champs.mot_modele.maxi} bind:value={j.mot_modele} oninput={() => (modifie = true)}></textarea>
          <span class="text-xs text-muted-foreground">{r.champs.mot_modele.aide}</span>
        </label>
        <label class="flex items-center gap-3 text-sm">
          <input type="color" class="h-9 w-12 rounded border bg-background" bind:value={j.accent} oninput={() => (modifie = true)} />
          <span><span class="text-muted-foreground">{r.champs.accent.libelle}</span> · {j.accent}</span>
        </label>
        <label class="flex items-center gap-3 text-sm">
          <input type="checkbox" bind:checked={j.larousse} onchange={() => (modifie = true)} />
          <span>Utiliser Larousse, Journaux de l'année (1966-2003)</span>
        </label>
      </div>
      <div class="mt-4 flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={!modifie || envoiJ}>Enregistrer</Button>
        {#if !modifie && !messageJ}<span class="text-xs text-muted-foreground">rien à enregistrer</span>{/if}
        {#if messageJ}<span class="text-sm" role="status">{messageJ}</span>{/if}
      </div>
      <p class="mt-3 text-xs text-muted-foreground">Impression : {r.lecture_seule ? 'lecture seule, rien ne part à l\'imprimante' : 'à venir (temps 3) ; PDF à imprimer pour l\'instant'}.</p>
    </form>
  {/if}

  {#if c}
    <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Top 5 culturel">
      <h2 class="text-lg font-semibold">Top 5 culturel</h2>
      <p class="mt-1 text-sm text-muted-foreground">Films, séries et musique de chaque année : la page 3 du livret (Musique, Cinéma) s'en sert. Préparé avec Claude, puis importé ici.</p>
      <dl class="mt-3 grid grid-cols-[8rem_1fr] gap-y-1 text-sm">
        <dt class="text-muted-foreground">Fichier</dt><dd>{c.source}{c.importe_le ? ` le ${c.importe_le.replace('T', ' ').slice(0, 16)}` : ''}</dd>
        <dt class="text-muted-foreground">Contenu</dt><dd>{c.lignes} lignes, de {c.annees[0]} à {c.annees[1]}</dd>
        <dt class="text-muted-foreground">À surveiller</dt><dd>{c.provisoires} provisoires, {c.a_verifier} « à vérifier »</dd>
      </dl>
      <ol class="mt-4 list-decimal space-y-1 pl-5 text-sm text-muted-foreground">
        <li>Télécharger le fichier actuel.</li>
        <li>Dans Claude, coller le prompt et joindre le fichier.</li>
        <li>Importer ici le fichier rendu par Claude (il est contrôlé avant d'être gardé).</li>
      </ol>
      <div class="mt-3 flex flex-wrap items-center gap-2">
        <a href="/api/culture/fichier" class="inline-flex h-9 items-center rounded-lg border px-3 text-sm hover:bg-secondary">Télécharger le fichier</a>
        <Button variant="outline" size="sm" onclick={copier}>{copie ? 'Prompt copié' : 'Copier le prompt'}</Button>
        <label class="inline-flex h-9 cursor-pointer items-center rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground">
          Importer un fichier<input type="file" accept=".csv,text/csv" class="sr-only" onchange={importer} />
        </label>
        {#if c.source === 'importé'}<Button variant="ghost" size="sm" onclick={revenir}>Revenir à la version livrée</Button>{/if}
      </div>
      {#if message}<p class="mt-3 text-sm" role="status">{message}</p>{/if}
      <details class="mt-3 text-sm" bind:open={voirPrompt}>
        <summary class="cursor-pointer text-muted-foreground">Voir le prompt</summary>
        <pre class="mt-2 max-h-80 overflow-auto rounded-lg border bg-background p-3 text-xs whitespace-pre-wrap">{c.prompt}</pre>
      </details>
    </section>
  {/if}

  <section class="mt-4 rounded-2xl border bg-card p-5">
    <h2 class="text-lg font-semibold">Règles</h2>
    <ul class="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
      <li>La une : le jour même, sinon la veille, la semaine, le mois — la portée est écrite au-dessus du titre.</li>
      <li>Drames (décès, attentats, catastrophes…) : jamais choisis seuls, sur aucun bloc ; visibles à la relecture avec leur raison.</li>
      <li>Textes en anglais : proposés en repli, jamais choisis seuls.</li>
      <li>L'année est toujours affichée ; l'âge en chiffres, jamais.</li>
      <li>Anniversaire à 14 jours ou moins du séjour : phrases proposées dans À traiter.</li>
    </ul>
  </section>

  <section class="mt-4 rounded-2xl border bg-card p-5">
    <h2 class="text-lg font-semibold">Journal</h2>
    {#if r.historique.length === 0}
      <p class="mt-1 text-sm text-muted-foreground">Rien pour l'instant.</p>
    {:else}
      <ul class="mt-2 grid gap-1 text-sm">
        {#each r.historique as h}
          <li class="flex gap-3"><span class="w-36 shrink-0 text-muted-foreground">{h.le.replace('T', ' ').slice(0, 16)}</span>
            <span>{GESTES[h.geste] ?? h.geste}{h.nom ? ' · ' + h.nom : ''}{h.detail ? ' · ' + h.detail : ''}</span></li>
        {/each}
      </ul>
    {/if}
  </section>
{/if}

<p class="mt-6 flex items-center justify-between gap-3 text-sm text-muted-foreground">
  <span>Gazette {session.version}</span>
  <Button variant="outline" onclick={deconnecter}>Se déconnecter</Button>
</p>
