namespace Toltech.FreeCAD
{

    /// <summary>
    /// Installe le module Python Toltech dans FreeCAD.
    /// </summary>
    public sealed class FreeCadModuleInstaller
    {
        private const string ModuleName = "Toltech";

        private readonly string _sourceDirectory;

        private readonly string _freeCadDirectory;

        public FreeCadModuleInstaller(
            string sourceDirectory,
            string freeCadDirectory)
        {
            _sourceDirectory = sourceDirectory;
            _freeCadDirectory = freeCadDirectory;
        }

        /// <summary>
        /// Installe ou met à jour le module Python Toltech.
        /// </summary>
        public void Install()
        {
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