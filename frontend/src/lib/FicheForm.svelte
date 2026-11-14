<script>
  // Saisie d'une fiche : nom affiché à la une, prénom (pour « Exemplaire de … »), date de naissance,
  // autres noms (tels qu'écrits dans la réservation de Home Assistant).
  import { Button } from '$lib/components/ui/button/index.js'
  let { valeur = {}, bouton = 'Créer la fiche', onvalider, onannuler = null } = $props()
  let nom = $state(valeur.nom ?? '')
  let prenom = $state(valeur.prenom ?? '')
  let naissance = $state(valeur.naissance ?? '')
  let alias = $state((valeur.alias ?? []).join(', '))
  let erreur = $state('')
  let envoi = $state(false)

  async function valider(e) {
    e.preventDefault()
    envoi = true
    erreur = ''
    try {
      await onvalider({ nom, prenom, naissance, alias: alias.split(',').map((a) => a.trim()).filter(Boolean) })
    } catch (err) {
      erreur = err.message
    }
    envoi = false
  }
</script>

<form onsubmit={valider} class="grid gap-3 sm:grid-cols-2">
  <label class="grid gap-1 text-sm">
    <span class="text-muted-foreground">Nom à la une</span>
    <input required bind:value={nom} placeholder="Prénom Nom" class="h-10 rounded-lg border bg-background px-3" />
  </label>
  <label class="grid gap-1 text-sm">
    <span class="text-muted-foreground">Prénom (« Exemplaire de … »)</span>
    <input bind:value={prenom} placeholder="le premier mot du nom" class="h-10 rounded-lg border bg-background px-3" />
  </label>
  <label class="grid gap-1 text-sm">
    <span class="text-muted-foreground">Date de naissance</span>
    <input required type="date" bind:value={naissance} class="h-10 rounded-lg border bg-background px-3" />
  </label>
  <label class="grid gap-1 text-sm">
    <span class="text-muted-foreground">Autres noms dans les réservations</span>
    <input bind:value={alias} placeholder="séparés par des virgules" class="h-10 rounded-lg border bg-background px-3" />
  </label>
  <div class="flex flex-wrap items-center gap-2 sm:col-span-2">
    <Button type="submit" disabled={envoi}>{bouton}</Button>
    {#if onannuler}<Button type="button" variant="outline" onclick={onannuler}>Annuler</Button>{/if}
    {#if erreur}<span class="text-sm text-destructive" role="alert">{erreur}</span>{/if}
  </div>
</form>
