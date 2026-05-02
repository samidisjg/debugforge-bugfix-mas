package main

import (
	"fmt"
	"os"
)

/**
 * File processor with a resource leak bug.
 * BUG: File is not properly closed in error cases.
 */

// ReadFileContent reads file content and returns it as string.
// BUG: Doesn't properly close file on error, causing resource leak.
func ReadFileContent(filename string) (string, error) {
	file, err := os.Open(filename)
	if err != nil {
		return "", err
	}
	defer file.Close() // This is correct, but shown for comparison

	// Reading large file into memory
	bytes := make([]byte, 1024*1024) // 1MB buffer
	n, err := file.Read(bytes)
	if err != nil {
		return "", err // File is properly closed by defer
	}

	return string(bytes[:n]), nil
}

// ProcessFiles processes multiple files - BUG: potential resource leak in loop.
func ProcessFiles(filenames []string) ([]string, error) {
	results := []string{}

	for _, filename := range filenames {
		file, err := os.Open(filename)
		if err != nil {
			// BUG: File handle not closed on error within loop
			return nil, fmt.Errorf("failed to open %s: %v", filename, err)
		}

		// Read file content
		bytes := make([]byte, 1024)
		n, err := file.Read(bytes)
		if err != nil {
			// BUG: File still open when returning error
			return nil, fmt.Errorf("failed to read %s: %v", filename, err)
		}

		results = append(results, string(bytes[:n]))
		file.Close() // File closed here, but not on error paths above
	}

	return results, nil
}

// GetFileSize returns the size of a file - BUG: doesn't check if file exists.
func GetFileSize(filename string) (int64, error) {
	info, err := os.Stat(filename)
	if err != nil {
		return 0, err
	}

	// BUG: Could return size for directory instead of file
	return info.Size(), nil
}

func main() {
	fmt.Println("File processor initialized")
}
