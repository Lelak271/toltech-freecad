namespace Toltech.FreeCAD
{
    /// <summary>
    /// Installe le module Python Toltech dans FreeCAD.
    /// </summary>
    public sealed class FreeCadModuleInstaller
    {
        private const string PreferredVersion = "v1-1";

        private const string CADName = "FreeCAD";
        private const string ModuleName = "Toltech";

        private readonly string _sourceDirectory;

        private readonly string _freeCadDirectory;

        public FreeCadModuleInstaller(
            string sourceDirectory)
        {
            _sourceDirectory = sourceDirectory;
            _freeCadDirectory = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                CADName,
                PreferredVersion);
        }

        /// <summary>
        /// Installe ou met à jour le module Python Toltech.
        /// Ne fait rien si FreeCAD n'est pas installé (ou jamais lancé).
        /// </summary>
        public void Install()
        {
            // FreeCAD absent : on ne crée rien dans le profil utilisateur
            if (!Directory.Exists(_freeCadDirectory))
            {
                return;
            }

            string targetDirectory =
                Path.Combine(
                    _freeCadDirectory,
                    "Mod",
                    ModuleName);

            Directory.CreateDirectory(
                targetDirectory);

            CopyFile(
                targetDirectory,
                "Init.py");

            CopyFile(
                targetDirectory,
                "InitGui.py");

            CopyFile(
                targetDirectory,
                "ToltechServer.py");

            CopyFile(
                targetDirectory,
                "ToltechPicker.py");
        }

        private void CopyFile(
            string targetDirectory,
            string fileName)
        {
            string source =
                Path.Combine(
                    _sourceDirectory,
                    fileName);

            string target =
                Path.Combine(
                    targetDirectory,
                    fileName);

            if (!File.Exists(source))
            {
                throw new FileNotFoundException(
                    $"FreeCAD module file not found: {source}");
            }

            File.Copy(
                source,
                target,
                overwrite: true);
        }
    }
}